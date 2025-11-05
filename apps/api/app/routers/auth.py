import random
import string

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

from ..settings import settings
from ..notifier import send_otp
from ..utils.redis_cache import get_redis_client

router = APIRouter(prefix="/v1/auth", tags=["auth"])

r = get_redis_client()

def _code(length: int = 6) -> str:
    """Generate a numeric OTP code."""
    return "".join(random.choices(string.digits, k=length))

class OTPRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None

@router.post("/otp:send")
def send_otp_endpoint(req: OTPRequest):
    """
    Dev: stores OTP in Redis as key otp:<dest>.
    Also returns dev_code in response when ENVIRONMENT=dev to make testing easy.
    """
    dest = req.email or req.phone
    if not dest:
        raise HTTPException(status_code=422, detail="Provide email or phone")

    code = _code()
    key = f"otp:{dest}"
    r.setex(key, settings.otp_ttl_seconds, code)
    send_otp(dest, code)

    resp = {"ok": True}
    if settings.environment == "dev":
        resp["dev_code"] = code  # DEV ONLY
    return resp

@router.get("/me")
def me(request: Request):
    email = request.cookies.get("demo_email")
    role  = request.cookies.get("demo_role")
    if not email or not role:
        return {"role": "ANON"}
    return {
        "email": email,
        "role": role,  # "PATIENT" | "CLINICIAN" | "OPS"
        # (optional) anything else your RoleGuard expects
    }
