from fastapi import APIRouter, Request, HTTPException
from app.core import security
from fastapi import Response

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me")
def me(request: Request):
    """Return basic info about the currently authenticated user.

    This endpoint reads the token from the Authorization header or from the
    HttpOnly cookie `octavia_token` and returns the token payload for debugging.
    """
    try:
        token = security.extract_token_from_request(authorization=request.headers.get("Authorization"), cookies=request.cookies)
        payload = security.decode_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        # Return limited payload for debugging (do not expose sensitive fields)
        return {"authenticated": True, "payload": {k: payload.get(k) for k in ("sub", "type", "exp")}}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Not authenticated")



@router.post("/logout")
def logout(response: Response):
    """Clear the authentication cookie (HttpOnly) on logout."""
    response.delete_cookie("octavia_token", path="/")
    return {"status": "ok"}
