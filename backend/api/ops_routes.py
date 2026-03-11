"""Operations Routes"""

from fastapi import APIRouter

from backend.api.schemas import OpsSnapshot
from backend.services.ops_service import OpsService


router = APIRouter(prefix="/ops", tags=["Operations"])


@router.get("/snapshot", response_model=OpsSnapshot)
async def get_ops_snapshot():
    svc = OpsService()
    return OpsSnapshot(**(await svc.snapshot()))
