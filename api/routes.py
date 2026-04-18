from fastapi import APIRouter, HTTPException, Query
from typing import Optional

router = APIRouter()

# Injected at startup
_service = None


def set_service(service):
    global _service
    _service = service


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/stats")
async def get_stats():
    if _service is None:
        raise HTTPException(503, "Monitoring service not initialized")
    return _service.stats()


@router.get("/deals")
async def get_deals(
    stage: Optional[str] = Query(None, description="Filter by stage ID"),
    assigned_by: Optional[str] = Query(None, description="Filter by assigned user ID"),
):
    if _service is None:
        raise HTTPException(503, "Monitoring service not initialized")
    deals = _service.snapshot()
    if stage:
        deals = [d for d in deals if d.stage_id == stage]
    if assigned_by:
        deals = [d for d in deals if d.assigned_by_id == assigned_by]
    return {"count": len(deals), "deals": [d.to_dict() for d in deals]}


@router.get("/deals/{deal_id}")
async def get_deal(deal_id: str):
    if _service is None:
        raise HTTPException(503, "Monitoring service not initialized")
    known = {d.id: d for d in _service.snapshot()}
    deal = known.get(deal_id)
    if not deal:
        raise HTTPException(404, f"Deal {deal_id} not found in current snapshot")
    return deal.to_dict()


@router.get("/stages")
async def get_stages():
    if _service is None:
        raise HTTPException(503, "Monitoring service not initialized")
    deals = _service.snapshot()
    stages = {}
    for d in deals:
        stages[d.stage_id] = stages.get(d.stage_id, 0) + 1
    return {"stages": [{"stage_id": k, "count": v} for k, v in stages.items()]}
