import logging
logger = logging.getLogger("notifier")

def send_otp(destination: str, code: str) -> None:
    print(f"[DEV] OTP to {destination}: {code}", flush=True)
    logger.info("Mock OTP sent to %s: %s", destination, code)

def send_email(to: str, subject: str, body: str) -> None:
    logger.info("Mock Email to %s: %s — %s", to, subject, body)

def send_sms(to: str, body: str) -> None:
    logger.info("Mock SMS to %s: %s", to, body)
    
def email_billing_staff(subject: str, body: str):
    print(f"[NOTIFY:BILLING] {subject}\n{body}")
    
try:
    from app.utils.notify import notify
    notify("billing", f"Eligibility follow-up created for {patient_email} (appt {appointment_id})")
except Exception as _:
    pass
    
    
