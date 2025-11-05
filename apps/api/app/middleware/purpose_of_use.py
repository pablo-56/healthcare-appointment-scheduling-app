# apps/api/app/middleware/purpose_of_use.py

from __future__ import annotations
from typing import Set, Optional
from fastapi import Header, HTTPException, Request, status



# --- DOC-ONLY header (shows up in OpenAPI) ---
def doc_purpose_of_use(
    x_purpose_of_use: str = Header(
        ...,
        alias="X-Purpose-Of-Use",
        description="Purpose-of-use code (e.g., OPERATIONS, TREATMENT, PAYMENT)",
    )
) -> str:
    # No logic here — purely to expose the header in Swagger.
    return x_purpose_of_use

# --- ENFORCER (does NOT declare header param, so it won't duplicate in docs) ---
def require_pou(allowed: Set[str]):
    async def _dep(request: Request):
        value = request.headers.get("x-purpose-of-use")
        if not value:
            raise HTTPException(status_code=400, detail="Missing X-Purpose-Of-Use header")
        code = value.strip().upper()
        if code not in allowed:
            raise HTTPException(status_code=403, detail=f"X-Purpose-Of-Use not allowed ({code})")
        # ok -> no return
    return _dep

# Use this dependency in route "dependencies=[Depends(pou_required({'OPERATIONS'}))]"
def pou_required(allowed: set[str]):
    async def _dep(x_purpose_of_use: str = Header(..., alias="X-Purpose-Of-Use")):
        val = (x_purpose_of_use or "").strip().upper()
        if val not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"X-Purpose-Of-Use must be one of {sorted(allowed)}",
            )
        return val
    return _dep