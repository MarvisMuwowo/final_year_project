# backend/app/API/email_utils.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_RECIPIENTS = os.getenv("SMTP_RECIPIENTS", "")

def send_alert_email(event_data: dict):
    """
    Send an email alert for a high priority event.
    """
    if not SMTP_USER or not SMTP_PASSWORD or not SMTP_RECIPIENTS:
        print("⚠️ Email credentials not configured. Skipping email alert.")
        return False

    recipients = [r.strip() for r in SMTP_RECIPIENTS.split(",") if r.strip()]

    if not recipients:
        print("⚠️ No recipients configured. Skipping email alert.")
        return False

    subject = f"🚨 SECURITY ALERT: High Priority Event {event_data.get('event_id', 'N/A')}"

    # Build HTML email body
    html_body = f"""
    <html>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f9; padding: 20px;">
        <div style="max-width: 650px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <div style="background: #dc2626; color: white; padding: 15px 20px; border-radius: 8px 8px 0 0; margin: -30px -30px 25px -30px;">
                <h2 style="margin: 0; font-size: 22px;">🚨 High Priority Security Event</h2>
            </div>
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <tr><td style="padding: 8px 0; font-weight: bold; width: 150px;">Event ID</td><td style="padding: 8px 0;">{event_data.get('event_id', 'N/A')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Priority</td><td style="padding: 8px 0; color: #dc2626; font-weight: bold;">{event_data.get('priority', 'High')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Risk Score</td><td style="padding: 8px 0;">{event_data.get('risk_score', 0.0):.4f}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Logged At</td><td style="padding: 8px 0;">{event_data.get('logged', 'N/A')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Computer</td><td style="padding: 8px 0;">{event_data.get('computer', 'N/A')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">User</td><td style="padding: 8px 0;">{event_data.get('user', 'N/A')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Task Category</td><td style="padding: 8px 0;">{event_data.get('task_category', 'N/A')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Status</td><td style="padding: 8px 0;">{event_data.get('status', 'unassigned')}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Assigned To</td><td style="padding: 8px 0;">{event_data.get('assigned_to', 'N/A')}</td></tr>
            </table>
            <div style="margin-top: 25px; padding-top: 15px; border-top: 1px solid #e5e7eb; font-size: 13px; color: #6b7280;">
                <p>This is an automated alert from the Security Log Prioritization System.</p>
                <p>Please investigate this event immediately.</p>
            </div>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = ", ".join(recipients)

    # Attach HTML part
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, recipients, msg.as_string())
        print(f"✅ Email alert sent to {len(recipients)} recipient(s)")
        return True
    except Exception as e:
        print(f"❌ Failed to send email alert: {e}")
        return False