"""
routers/assets.py

GET    /assets              — List all files in the Vector Store (paginated)
DELETE /assets/{file_id}   — Remove a file from Vector Store + OpenAI Files

Headers  : Authorization: Bearer <Firebase ID Token>
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query

from ..auth import verify_admin
from ..vector_store import delete_file_from_vector_store, list_vector_store_files

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/assets")
async def get_assets(
    limit: int = Query(100, ge=1, le=100),
    after: str | None = Query(None, description="Pagination cursor"),
    uid: str = Depends(verify_admin),
):
    """Return a paginated list of all files in the shared Vector Store."""
    try:
        files, last_id, has_more = await list_vector_store_files(limit=limit, after=after)
    except Exception as exc:
        logger.exception("Failed to list assets for admin %s: %s", uid, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch assets: {exc}",
        ) from exc

    return {
        "assets": [
            {
                "file_id": f.file_id,
                "filename": f.filename,
                "created_at": f.created_at,
                "status": f.status,
            }
            for f in files
        ],
        "has_more": has_more,
        "last_id": last_id,
    }


@router.delete("/assets/{file_id}")
async def delete_asset(file_id: str, uid: str = Depends(verify_admin)):
    """Remove a file from the Vector Store and delete it from OpenAI Files."""
    logger.info("Admin %s attempting to delete file %s", uid, file_id)
    try:
        await delete_file_from_vector_store(file_id)
        logger.info("Successfully deleted file %s for admin %s", file_id, uid)
    except ValueError as exc:
        logger.error("Failed to delete asset %s for admin %s: File not found", file_id, uid)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File does not exist.",
        ) from exc
    except Exception as exc:
        logger.exception(
            "Failed to delete asset %s for admin %s: %s", file_id, uid, exc
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete asset: {exc}",
        ) from exc

    return {
        "status": "success",
        "file_id": file_id,
        "message": "File deleted successfully."
    }
