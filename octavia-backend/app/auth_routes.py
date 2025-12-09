from fastapi import APIRouter, Request, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from app.core import security
from app.core.database import get_db
from app.models import User
from datetime import datetime

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    """Return full user info for the currently authenticated user.
    
    This endpoint reads the token from the Authorization header or from the
    HttpOnly cookie `octavia_token` and returns the user object.
    """
    print("🔍 /me endpoint called")  # Debug
    print(f"   Headers: {dict(request.headers)}")  # Debug
    print(f"   Cookies: {dict(request.cookies)}")  # Debug
    
    try:
        # Extract token from Authorization header or cookie
        token = security.extract_token_from_request(
            authorization=request.headers.get("Authorization"), 
            cookies=request.cookies
        )
        
        if not token:
            print("❌ No token found in request")
            raise HTTPException(status_code=401, detail="Not authenticated - no token")
        
        print(f"✅ Token found: {token[:20]}...")
        
        # Decode token to get user ID
        payload = security.decode_token(token)
        if not payload:
            print("❌ Token decode failed")
            raise HTTPException(status_code=401, detail="Invalid token")
        
        print(f"✅ Token payload: {payload}")
        
        # Get user from database
        user_id = payload.get("sub")
        if not user_id:
            print("❌ No 'sub' in token payload")
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        print(f"🔍 Looking up user_id: {user_id}")
        
        # Try to convert to int if it's a string
        try:
            user_id_int = int(user_id)
            print(f"✅ Converted user_id to int: {user_id_int}")
        except (ValueError, TypeError) as e:
            print(f"❌ Invalid user_id format: {user_id}, type: {type(user_id)}, error: {e}")
            raise HTTPException(status_code=401, detail=f"Invalid user ID format in token: {user_id}")
        
        # Query user - try both with ID as int and as string just in case
        user = db.query(User).filter(User.id == user_id_int).first()
        
        # If not found, also try treating the field as string (some DBs store it differently)
        if not user:
            print(f"⚠️  User not found with int ID, trying string lookup...")
            user = db.query(User).filter(User.id == str(user_id)).first()
        if not user:
            print(f"❌ User not found: {user_id_int}")
            raise HTTPException(status_code=404, detail="User not found")
        
        print(f"✅ User found: {user.email}")
        
        # Build response with all fields, using getattr with defaults for optional fields
        response_data = {
            "id": user.id,
            "email": user.email,
            "is_verified": getattr(user, 'is_verified', False),
            "authenticated": True
        }
        
        # Add optional fields if they exist
        if hasattr(user, 'credits'):
            response_data["credits"] = user.credits
        else:
            response_data["credits"] = 0.0
            
        if hasattr(user, 'created_at'):
            created_at = user.created_at
            if created_at:
                if isinstance(created_at, datetime):
                    response_data["created_at"] = created_at.isoformat()
                else:
                    response_data["created_at"] = str(created_at)
            else:
                response_data["created_at"] = None
        else:
            response_data["created_at"] = None
        
        if hasattr(user, 'name') and user.name:
            response_data["name"] = user.name
        
        print(f"✅ Returning user data: {response_data}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ /me endpoint error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")


@router.post("/logout")
def logout(response: Response):
    """Clear the authentication cookie (HttpOnly) on logout."""
    response.delete_cookie(
        key="octavia_token",
        path="/",
        samesite="none",
        secure=False  # Set to True in production with HTTPS
    )
    return {"status": "ok", "message": "Logged out successfully"}


@router.get("/debug")
def debug_auth(request: Request):
    """Debug endpoint to check what authentication data is present"""
    auth_header = request.headers.get("Authorization")
    cookies = dict(request.cookies)
    
    token = None
    token_source = None
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        token_source = "Authorization header"
    elif "octavia_token" in cookies:
        token = cookies["octavia_token"]
        token_source = "Cookie"
    
    payload = None
    if token:
        payload = security.decode_token(token)
    
    return {
        "has_auth_header": bool(auth_header),
        "auth_header_preview": auth_header[:50] if auth_header else None,
        "cookies": list(cookies.keys()),
        "has_token": bool(token),
        "token_source": token_source,
        "token_preview": token[:20] + "..." if token else None,
        "payload": payload,
        "all_headers": dict(request.headers)
    }