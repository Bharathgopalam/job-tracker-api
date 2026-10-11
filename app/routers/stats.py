from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..domain import INTERVIEWED, RESPONDED, Status
from ..models import Application, User
from ..schemas import StatsOut

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(
        select(Application.status, func.count()).where(Application.user_id == user.id)
        .group_by(Application.status)
    ).all()
    by_status = {s.value: 0 for s in Status}
    by_status.update({status: count for status, count in rows})

    total = sum(by_status.values())
    submitted = db.scalar(
        select(func.count()).where(Application.user_id == user.id, Application.applied_on.is_not(None))
    ) or 0
    responded = sum(by_status[s.value] for s in RESPONDED)
    interviewed = sum(by_status[s.value] for s in INTERVIEWED)

    return StatsOut(
        total=total,
        submitted=submitted,
        by_status=by_status,
        response_rate=round(responded / submitted * 100, 1) if submitted else 0.0,
        interview_rate=round(interviewed / submitted * 100, 1) if submitted else 0.0,
    )
