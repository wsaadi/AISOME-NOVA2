import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app.middleware.auth import require_permission, get_current_user
from app.services.updater import get_update_service
from app.models.user import User

router = APIRouter(prefix="/api/system", tags=["System"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
LOGO_FILENAME = "platform_logo"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".webp"}


@router.get("/version")
async def get_version(current_user: User = Depends(get_current_user)):
    service = get_update_service()
    return {"version": service.get_current_version()}


@router.get("/check-update")
async def check_updates(current_user: User = Depends(require_permission("system", "read"))):
    service = get_update_service()
    return service.check_for_updates()


@router.post("/update")
async def apply_update(current_user: User = Depends(require_permission("system", "update"))):
    service = get_update_service()
    return service.apply_update()


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("system", "update")),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Use: {', '.join(ALLOWED_EXTENSIONS)}")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Remove any existing logo
    for f in os.listdir(UPLOAD_DIR):
        if f.startswith(LOGO_FILENAME):
            os.remove(os.path.join(UPLOAD_DIR, f))

    dest = os.path.join(UPLOAD_DIR, f"{LOGO_FILENAME}{ext}")
    with open(dest, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    return {"success": True, "filename": f"{LOGO_FILENAME}{ext}"}


@router.get("/logo")
async def get_logo():
    if not os.path.isdir(UPLOAD_DIR):
        raise HTTPException(status_code=404, detail="No logo uploaded")
    for f in os.listdir(UPLOAD_DIR):
        if f.startswith(LOGO_FILENAME):
            return FileResponse(os.path.join(UPLOAD_DIR, f))
    raise HTTPException(status_code=404, detail="No logo uploaded")


@router.delete("/logo")
async def delete_logo(
    current_user: User = Depends(require_permission("system", "update")),
):
    if os.path.isdir(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            if f.startswith(LOGO_FILENAME):
                os.remove(os.path.join(UPLOAD_DIR, f))
                return {"success": True}
    raise HTTPException(status_code=404, detail="No logo to delete")
