from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
import numpy as np
from app.API.dependencies import get_cache, get_model

router = APIRouter(prefix="/shap", tags=["SHAP Explainability"])

CLASS_LABELS = {
    0: "Auditing settings on object were changed.",
    1: "Logon",
    2: "Other",
    3: "Special Logon",
    4: "User Account Management",
}

class SHAPResult(BaseModel):
    event_index: int
    predicted_class: int
    predicted_label: str
    base_value: float
    feature_names: list
    feature_values: list
    shap_values: list
    top_features: list
    interpretation: str


@router.get("/event/{event_index}", response_model=SHAPResult)
def get_shap_for_event(event_index: int, authorization: str = Header(None)):
    cache = get_cache()
    X_test = cache.get("X_test")
    shap_values = cache.get("shap_values")
    explainer = cache.get("explainer")
    result = cache.get("result")
    
    if X_test is None:
        raise HTTPException(503, "Cache not ready")
    if event_index >= len(X_test):
        raise HTTPException(404, f"Event {event_index} not found. Max: {len(X_test)-1}")
    
    model = get_model()
    predicted_class = int(model.predict(X_test.iloc[[event_index]])[0])
    predicted_label = CLASS_LABELS.get(predicted_class, str(predicted_class))
    
    # Handle SHAP values properly
    # shap_values is typically a list of arrays [class0_shap, class1_shap, ...]
    # or a single array for binary classification
    if isinstance(shap_values, list):
        # Multi-class case
        if predicted_class < len(shap_values):
            shap_array = shap_values[predicted_class]
        else:
            shap_array = shap_values[0]
        # Get the SHAP values for this event
        event_shap = shap_array[event_index]
    else:
        # Binary case
        event_shap = shap_values[event_index]
    
    # Convert to flat list if it's a numpy array
    if hasattr(event_shap, 'tolist'):
        event_shap = event_shap.tolist()
    
    # If it's still a list of lists, flatten or take first
    if isinstance(event_shap, list) and len(event_shap) > 0:
        if isinstance(event_shap[0], list):
            # Flatten the list if needed
            event_shap = [item for sublist in event_shap for item in sublist]
    
    # Get base value
    if hasattr(explainer, 'expected_value'):
        if isinstance(explainer.expected_value, list):
            if predicted_class < len(explainer.expected_value):
                base_value = float(explainer.expected_value[predicted_class])
            else:
                base_value = float(explainer.expected_value[0])
        else:
            base_value = float(explainer.expected_value)
    else:
        base_value = 0.0
    
    feature_names = X_test.columns.tolist()
    feature_values = X_test.iloc[event_index].tolist()
    
    # Ensure lengths match
    min_len = min(len(event_shap) if isinstance(event_shap, list) else len(feature_names), len(feature_names))
    if isinstance(event_shap, list):
        event_shap = event_shap[:min_len]
    else:
        # If event_shap is a scalar, create a list
        event_shap = [float(event_shap)] * min_len
    
    feature_names = feature_names[:min_len]
    feature_values = feature_values[:min_len]
    
    # Create top features list
    top_features = []
    for i in range(min_len):
        shap_val = float(event_shap[i]) if i < len(event_shap) else 0.0
        top_features.append({
            "feature": feature_names[i],
            "value": round(float(feature_values[i]), 4),
            "shap": round(shap_val, 4),
            "direction": "increases risk" if shap_val > 0 else "reduces risk"
        })
    
    top_features.sort(key=lambda x: abs(x["shap"]), reverse=True)
    
    # Get priority
    priority = "Low"
    if result is not None and event_index < len(result):
        priority = str(result.iloc[event_index].get("priority", "Low"))
    
    # Build interpretation
    if top_features and len(top_features) > 0:
        top = top_features[0]
        interpretation = f"Event {event_index} classified as '{predicted_label}' (Priority: {priority}). "
        interpretation += f"Main factor: '{top['feature']}' = {top['value']} "
        interpretation += f"({'increased' if top['shap'] > 0 else 'reduced'} risk by {abs(top['shap']):.3f})."
        
        # Add second factor if available
        if len(top_features) > 1:
            second = top_features[1]
            interpretation += f" Secondary: '{second['feature']}' = {second['value']} "
            interpretation += f"({'increased' if second['shap'] > 0 else 'reduced'} risk by {abs(second['shap']):.3f})."
    else:
        interpretation = f"No SHAP data available for event {event_index}."
    
    return SHAPResult(
        event_index=event_index,
        predicted_class=predicted_class,
        predicted_label=predicted_label,
        base_value=round(base_value, 4),
        feature_names=feature_names,
        feature_values=[round(float(v), 4) for v in feature_values],
        shap_values=[round(float(v), 4) for v in event_shap],
        top_features=top_features[:8],
        interpretation=interpretation
    )