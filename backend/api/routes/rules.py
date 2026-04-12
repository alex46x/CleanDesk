"""
api/routes/rules.py — CRUD endpoints for classification rules.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_db
from backend.database.models import Rule
from backend.schemas.schemas import RuleCreate, RuleResponse, RuleUpdate

router = APIRouter(prefix="/rules", tags=["Rules"])


@router.get("/", response_model=list[RuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db)) -> list[RuleResponse]:
    result = await db.execute(select(Rule).order_by(Rule.priority.desc()))
    return [RuleResponse.model_validate(r) for r in result.scalars().all()]


@router.post("/", response_model=RuleResponse, status_code=201)
async def create_rule(
    payload: RuleCreate, db: AsyncSession = Depends(get_db)
) -> RuleResponse:
    rule = Rule(**payload.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return RuleResponse.model_validate(rule)


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int, payload: RuleUpdate, db: AsyncSession = Depends(get_db)
) -> RuleResponse:
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = payload.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(rule, key, value)

    await db.commit()
    await db.refresh(rule)
    return RuleResponse.model_validate(rule)


@router.delete("/{rule_id}", status_code=204, response_class=Response)
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)) -> Response:
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
    await db.commit()
    return Response(status_code=204)
