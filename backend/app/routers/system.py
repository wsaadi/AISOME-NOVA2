from fastapi import APIRouter, Depends
from app.middleware.auth import require_permission, get_current_user
from app.services.updater import get_update_service
from app.models.user import User

router = APIRouter(prefix="/api/system", tags=["System"])


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
