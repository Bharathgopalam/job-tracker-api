from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..domain import Status, allowed_next, can_transition
from ..models import Application, User
from ..schemas import ApplicationCreate, ApplicationOut, ApplicationUpdate, Page, StatusChange

router = APIRouter(prefix="/applications", tags=["applications"])


def _get_owned(db: Session, user: User, app_id: int) -> Application:
    """Fetch an application belonging to the user. Other users' ids look like 404s."""
    app = db.scalar(select(Application).where(Application.id == app_id, Application.user_id == user.id))
    if app is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return app


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    app = Application(user_id=user.id, status=Status.WISHLIST.value, **payload.model_dump())
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.get("", response_model=Page)
def list_applications(
    status_filter: Optional[Status] = Query(None, alias="status"),
    q: Optional[str] = Query(None, max_length=100, description="Search company, role and notes"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Application).where(Application.user_id == user.id)
    if status_filter:
        stmt = stmt.where(Application.status == status_filter.value)
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        stmt = stmt.where(or_(
            Application.company.ilike(like, escape="\\"),
            Application.role.ilike(like, escape="\\"),
            Application.notes.ilike(like, escape="\\"),
        ))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(Application.updated_at.desc(), Application.id.desc()).limit(limit).offset(offset)
    ).all()
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{app_id}", response_model=ApplicationOut)
def get_application(app_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _get_owned(db, user, app_id)


@router.patch("/{app_id}", response_model=ApplicationOut)
def update_application(app_id: int, payload: ApplicationUpdate, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    app = _get_owned(db, user, app_id)
    changes = payload.model_dump(exclude_unset=True)
    for required in ("company", "role"):
        if required in changes and changes[required] is None:
            raise HTTPException(422, f"{required} cannot be null")

    new_min = changes.get("salary_min", app.salary_min)
    new_max = changes.get("salary_max", app.salary_max)
    if new_min is not None and new_max is not None and new_min > new_max:
        raise HTTPException(422,
                            "salary_min must be less than or equal to salary_max")

    for field, value in changes.items():
        setattr(app, field, value)
    db.commit()
    db.refresh(app)
    return app


@router.post("/{app_id}/status", response_model=ApplicationOut)
def change_status(app_id: int, payload: StatusChange, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    app = _get_owned(db, user, app_id)
    current = Status(app.status)
    if not can_transition(current, payload.status):
        allowed = ", ".join(s.value for s in allowed_next(current)) or "none (final state)"
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot move from '{current.value}' to '{payload.status.value}'. Allowed: {allowed}",
        )
    app.status = payload.status.value
    if payload.status is Status.APPLIED and app.applied_on is None:
        app.applied_on = date.today()
    db.commit()
    db.refresh(app)
    return app


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(app_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    app = _get_owned(db, user, app_id)
    db.delete(app)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
