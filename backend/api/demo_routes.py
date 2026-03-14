"""Demo Scenario Routes"""

from fastapi import APIRouter, Depends

from backend.api.schemas import DemoScenarioResult
from backend.services.demo_service import DemoService
from backend.services.auth_dependencies import require_roles
from backend.services.auth_service import UserRole


router = APIRouter(prefix="/demo", tags=["Demo"])


@router.post("/geofence-violation", response_model=DemoScenarioResult)
async def setup_geofence_violation(
    current_user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    svc = DemoService()
    return DemoScenarioResult(**(await svc.scenario_geofence_violation()))


@router.post("/stationary", response_model=DemoScenarioResult)
async def setup_stationary_behavior(
    device_id: str = "TRK101",
    current_user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    svc = DemoService()
    return DemoScenarioResult(**(await svc.scenario_stationary_device(device_id=device_id)))
