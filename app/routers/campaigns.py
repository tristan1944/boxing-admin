from __future__ import annotations

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db, require_token
from ..models import FacebookCampaign


router = APIRouter(prefix="/api", tags=["campaigns"], dependencies=[Depends(require_token)])


@router.get("/campaigns.list")
def campaigns_list(db: Session = Depends(get_db)) -> dict:
    items = db.execute(select(FacebookCampaign)).scalars().all()
    return {
        "items": [
            {"id": c.id, "name": c.name, "platform": c.platform}
            for c in items
        ],
        "total": len(items),
    }


