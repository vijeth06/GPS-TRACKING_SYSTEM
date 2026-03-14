"""Rule engine routes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.api.schemas import RuleDefinition, RuleEvaluationResult, RuleResponse
from backend.services.auth_dependencies import require_roles
from backend.services.auth_service import UserRole
from backend.services.rule_engine_service import RuleEngineService


router = APIRouter(prefix="/rules", tags=["Rule Engine"])


@router.get("", response_model=List[RuleResponse])
async def list_rules(current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER]))):
    _ = current_user
    svc = RuleEngineService()
    return await svc.list_rules()


@router.post("", response_model=RuleResponse)
async def create_rule(
    payload: RuleDefinition,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
):
    _ = current_user
    svc = RuleEngineService()
    return await svc.create_rule(payload.model_dump())


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: str,
    payload: RuleDefinition,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
):
    _ = current_user
    svc = RuleEngineService()
    row = await svc.update_rule(rule_id, payload.model_dump())
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
    return row


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: str,
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    _ = current_user
    svc = RuleEngineService()
    ok = await svc.delete_rule(rule_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"deleted": True}


@router.post("/evaluate/{event_type}", response_model=RuleEvaluationResult)
async def evaluate_rule_event(
    event_type: str,
    payload: dict,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
):
    _ = current_user
    svc = RuleEngineService()
    return await svc.evaluate_event(event_type, payload)
