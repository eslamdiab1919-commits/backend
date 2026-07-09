"""
app/auth.py

FastAPI dependency that verifies the Firebase ID token from the
Authorization: Bearer <token> header.

Usage:
    @router.post("/some-endpoint")
    async def handler(uid: str = Depends(verify_token)):
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from firebase_admin import auth, firestore_async

_bearer = HTTPBearer()


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """
    Verify a Firebase ID token.

    Returns the authenticated user's UID on success.
    Raises HTTP 401 on any authentication failure.
    """
    try:
        decoded = auth.verify_id_token(credentials.credentials)
        return decoded["uid"]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired Firebase ID token: {exc}",
        ) from exc


async def verify_admin(uid: str = Depends(verify_token)) -> str:
    """
    Verify that the authenticated user has the 'admin' role in Firestore.
    """
    try:
        db = firestore_async.client()
        user_doc = await db.collection("users").document(uid).get()
        if not user_doc.exists or user_doc.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required.",
            )
        return uid
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying admin status: {exc}",
        ) from exc
