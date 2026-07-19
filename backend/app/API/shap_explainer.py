# backend/app/API/shap_explainer.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import numpy as np
import logging
import pandas as pd
import shap

from app.API.dependencies import get_current_user, get_cache, get_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shap", tags=["SHAP Explainability"])

# Fallback labels (used only if target_encoder is missing)
CLASS_LABELS = {
    0: "Auditing settings on object were changed.",
    1: "Logon",
    2: "Other",
    3: "Special Logon",
    4: "User Account Management",
}

class SHAPResult(BaseModel):
    event_id        : int
    predicted_class : int
    predicted_label : str
    base_value      : float
    feature_names   : list
    feature_values  : list
    shap_values     : list
    top_features    : list
    interpretation  : str

def _build_interpretation(top_features, predicted_label, priority, event_id, encoders=None):
    if not top_features:
        return f"No SHAP data for event {event_id}."

    features = [f for f in top_features if f["feature"] != "event_id"]
    if not features:
        return f"Event {event_id}: only 'event_id' had SHAP values – no meaningful explanation."

    salient = features[:5]

    def get_display_value(feature_name, raw_value):
        if encoders and feature_name in encoders:
            try:
                le = encoders[feature_name]
                return le.inverse_transform([int(round(raw_value))])[0]
            except Exception:
                pass
        return raw_value

    explanation = f"Event #{event_id} was classified as **{predicted_label}** with **{priority}** priority.\n\n"
    explanation += "Key factors (in order of importance):\n"

    for i, item in enumerate(salient, 1):
        feat = item["feature"]
        val_display = get_display_value(feat, item["value"])
        dir_str = item["direction"]
        abs_shap = abs(item["shap"])
        if abs_shap > 0.5:
            strength = "very strongly"
        elif abs_shap > 0.2:
            strength = "strongly"
        else:
            strength = "moderately"

        explanation += (
            f"{i}. **{feat}** (value: {val_display}) – "
            f"{dir_str} {strength} (SHAP magnitude: {abs_shap:.3f}).\n"
        )

    total_pos = sum(item["shap"] for item in salient if item["shap"] > 0)
    total_neg = sum(abs(item["shap"]) for item in salient if item["shap"] < 0)

    if total_pos > total_neg * 1.1:
        overall = "increased"
        contrast = "decreased"
    elif total_neg > total_pos * 1.1:
        overall = "decreased"
        contrast = "increased"
    else:
        overall = "had no clear net effect on"
        contrast = ""

    if overall != "had no clear net effect on":
        explanation += (
            f"\nOverall, the combined influence of these factors **{overall}** "
            f"the likelihood of this classification (with {contrast} effects being weaker)."
        )
    else:
        explanation += (
            "\nOverall, the positive and negative influences balanced out, "
            "resulting in this classification."
        )

    # Contextual note (using predicted_label from target_encoder)
    if "Auditing settings" in predicted_label:
        explanation += " This event pertains to modifications of auditing configuration."
    elif "Logon" in predicted_label:
        explanation += " This event matches typical logon characteristics."
    elif "Special Logon" in predicted_label:
        explanation += " This event shows signs of a privileged or service logon."
    elif "User Account Management" in predicted_label:
        explanation += " This event involves changes to user accounts."
    elif predicted_label == "Other":
        explanation += " This event did not exhibit strong patterns of Logon, Account Management, or Special Logon, so it was grouped as Other."

    if priority == "High":
        explanation += " **High priority – investigate promptly.**"

    return explanation

@router.get("/available-events")
def get_available_events(current_user: dict = Depends(get_current_user)):
    cache = get_cache()
    result = cache.get("result")
    if result is None:
        raise HTTPException(status_code=503, detail="Cache not ready")
    events = result[["id", "priority"]].to_dict(orient="records")
    return {"events": events, "total": len(events)}

@router.get("/debug-cache")
def debug_cache(current_user: dict = Depends(get_current_user)):
    cache = get_cache()
    result = cache.get("result")
    X_test = cache.get("X_test")
    shap_values = cache.get("shap_values")
    if result is None or X_test is None or shap_values is None:
        return {"error": "Cache missing"}
    shap_len = shap_values[0].shape[0] if isinstance(shap_values, list) else shap_values.shape[0]
    return {
        "result_len": len(result),
        "X_test_shape": X_test.shape[0],
        "shap_rows": shap_len,
        "active_model": cache.get("active_model", "unknown")
    }

@router.get("/event/{event_id}", response_model=SHAPResult)
def get_shap_for_event(event_id: int, current_user: dict = Depends(get_current_user)):
    # Get model and cache
    model = get_model()
    cache = get_cache()
    result = cache.get("result")
    encoders = cache.get("encoders", {})
    X_test = cache.get("X_test")
    shap_values = cache.get("shap_values")
    explainer = cache.get("explainer")
    target_encoder = cache.get("target_encoder", None)  # ← get target encoder

    if result is None:
        raise HTTPException(503, "Cache not ready (result missing)")

    # Find the row index using 'id'
    mask = result["id"] == event_id
    if not mask.any():
        raise HTTPException(404, f"Event with ID {event_id} not found in cache")

    row_number = result.index[mask].tolist()[0]

    # ---- Check if we have SHAP values for this row ----
    use_cached_shap = True
    if shap_values is None:
        use_cached_shap = False
        logger.warning(f"shap_values is None, falling back to on‑the‑fly computation for event {event_id}")
    else:
        if isinstance(shap_values, list):
            shap_rows = shap_values[0].shape[0]
        else:
            shap_rows = shap_values.shape[0]
        logger.info(f"shap_values has {shap_rows} rows, requested row {row_number}")
        if row_number >= shap_rows:
            logger.warning(f"Requested row {row_number} out of cached SHAP (size {shap_rows}), falling back to on‑the‑fly")
            use_cached_shap = False

    # ---- If cached SHAP is not available or out of bounds, compute on the fly ----
    if not use_cached_shap:
        logger.info(f"Computing SHAP on the fly for event {event_id}")
        if X_test is None:
            raise HTTPException(503, "X_test not available for on‑the‑fly computation")
        # Get the feature row
        X_row = X_test.iloc[[row_number]].copy()
        # Compute SHAP for this single row
        if explainer is None:
            explainer = shap.TreeExplainer(model)
        # We need the predicted class first
        raw_pred = model.predict(X_row)
        predicted_class = int(round(float(raw_pred[0])))
        # Get SHAP values for this row (all classes)
        shap_vals_all = explainer.shap_values(X_row)
        # Select the predicted class
        if isinstance(shap_vals_all, list):
            event_shap = np.array(shap_vals_all[predicted_class]).flatten()
        else:
            event_shap = np.array(shap_vals_all).flatten()
        # Base value
        ev = explainer.expected_value
        if isinstance(ev, (list, np.ndarray)):
            base_value = float(ev[predicted_class]) if predicted_class < len(ev) else float(ev[0])
        else:
            base_value = float(ev)
        # Feature names and values
        feature_names = list(X_row.columns)
        feature_values = X_row.iloc[0].tolist()
        # Build top features and interpretation
        top_features = sorted(
            [
                {"feature": feature_names[i],
                 "value": round(float(feature_values[i]), 4),
                 "shap": round(float(event_shap[i]), 4),
                 "direction": "increases risk" if event_shap[i] > 0 else "reduces risk"}
                for i in range(len(feature_names))
            ],
            key=lambda x: abs(x["shap"]),
            reverse=True
        )[:10]

        # ── Decode label using target_encoder ──
        if target_encoder is not None:
            try:
                predicted_label = target_encoder.inverse_transform([predicted_class])[0]
            except Exception as e:
                logger.warning(f"Failed to decode with target_encoder: {e}, falling back to CLASS_LABELS")
                predicted_label = CLASS_LABELS.get(predicted_class, str(predicted_class))
        else:
            predicted_label = CLASS_LABELS.get(predicted_class, str(predicted_class))

        priority = str(result.iloc[row_number].get("priority", "Unknown"))
        interpretation = _build_interpretation(top_features, predicted_label, priority, event_id, encoders)

        return SHAPResult(
            event_id=event_id,
            predicted_class=predicted_class,
            predicted_label=predicted_label,
            base_value=round(base_value, 4),
            feature_names=feature_names,
            feature_values=[round(float(v), 4) for v in feature_values],
            shap_values=[round(float(v), 4) for v in event_shap],
            top_features=top_features,
            interpretation=interpretation
        )

    # ---- If we reach here, we are using cached SHAP ----
    if X_test is None:
        raise HTTPException(503, "X_test not available")

    # Predict (we need the class for extracting SHAP)
    X_row = X_test.iloc[[row_number]].copy()
    raw_pred = model.predict(X_row)
    predicted_class = int(round(float(raw_pred[0])))
    # Clamp to valid range
    n_classes = len(target_encoder.classes_) if target_encoder is not None else len(CLASS_LABELS)
    if predicted_class < 0 or predicted_class >= n_classes:
        predicted_class = 0

    # ── Decode label using target_encoder ──
    if target_encoder is not None:
        try:
            predicted_label = target_encoder.inverse_transform([predicted_class])[0]
        except Exception as e:
            logger.warning(f"Failed to decode with target_encoder: {e}, falling back to CLASS_LABELS")
            predicted_label = CLASS_LABELS.get(predicted_class, str(predicted_class))
    else:
        predicted_label = CLASS_LABELS.get(predicted_class, str(predicted_class))

    # Extract SHAP from cached array
    try:
        if isinstance(shap_values, list):
            cls_idx = predicted_class if predicted_class < len(shap_values) else 0
            shap_array = shap_values[cls_idx]
        else:
            shap_array = shap_values
        # Double check row
        if row_number >= shap_array.shape[0]:
            raise HTTPException(500, f"Row {row_number} out of cached SHAP (size {shap_array.shape[0]})")
        event_shap = np.array(shap_array[row_number]).flatten()
        feature_names = list(X_row.columns)
        feature_values = X_row.iloc[0].tolist()
        # Trim to match
        n = min(len(event_shap), len(feature_names), len(feature_values))
        event_shap = event_shap[:n]
        feature_names = feature_names[:n]
        feature_values = feature_values[:n]
        # Base value
        ev = explainer.expected_value
        if isinstance(ev, (list, np.ndarray)):
            base_value = float(ev[predicted_class]) if predicted_class < len(ev) else float(ev[0])
        else:
            base_value = float(ev)
        # Build top features
        top_features = sorted(
            [
                {"feature": feature_names[i],
                 "value": round(float(feature_values[i]), 4),
                 "shap": round(float(event_shap[i]), 4),
                 "direction": "increases risk" if event_shap[i] > 0 else "reduces risk"}
                for i in range(len(feature_names))
            ],
            key=lambda x: abs(x["shap"]),
            reverse=True
        )[:10]
        priority = str(result.iloc[row_number].get("priority", "Unknown"))
        interpretation = _build_interpretation(top_features, predicted_label, priority, event_id, encoders)

        return SHAPResult(
            event_id=event_id,
            predicted_class=predicted_class,
            predicted_label=predicted_label,
            base_value=round(base_value, 4),
            feature_names=feature_names,
            feature_values=[round(float(v), 4) for v in feature_values],
            shap_values=[round(float(v), 4) for v in event_shap],
            top_features=top_features,
            interpretation=interpretation
        )

    except Exception as e:
        logger.error(f"SHAP extraction from cache failed: {e}")
        raise HTTPException(500, f"SHAP extraction failed: {e}")

@router.get("/summary")
def get_shap_summary(current_user: dict = Depends(get_current_user)):
    cache = get_cache()
    shap_values = cache.get("shap_values")
    X_test = cache.get("X_test")
    if X_test is None or shap_values is None:
        raise HTTPException(503, "SHAP cache not ready")
    feature_names = list(X_test.columns)
    if isinstance(shap_values, list):
        all_shap = np.abs(np.array(shap_values))
    else:
        all_shap = np.abs(np.array(shap_values))[np.newaxis, ...]
    mean_abs = all_shap.mean(axis=(0, 1)).tolist()
    mean_abs = mean_abs[:len(feature_names)]
    ranked = sorted(zip(feature_names, mean_abs), key=lambda x: x[1], reverse=True)
    return {
        "feature_names": [r[0] for r in ranked],
        "mean_absolute_shap": [round(r[1], 6) for r in ranked],
        "most_influential": ranked[0][0] if ranked else "N/A"
    }