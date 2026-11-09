import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.incident import (
    IncidentListResponse,
    IncidentResponse,
    IncidentSummaryResponse,
)
from app.services.incident_query_service import IncidentQueryService


router = APIRouter(
    prefix="/incidents",
    tags=["Incidents"],
)


@router.get("/summary",response_model=IncidentSummaryResponse)
def get_incident_summary(db: Session = Depends(get_db)):
    service = IncidentQueryService(db)
    return service.get_summary()


@router.get("",response_model=IncidentListResponse)
def list_incidents(
    status: str | None = Query(
        default=None,
        pattern="^(open|acknowledged|resolved)$"),
    severity: str | None = Query(default=None, min_length=1),
    namespace: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)):
    service = IncidentQueryService(db)

    incidents, total = service.list_incidents(
        status=status,
        severity=severity,
        namespace=namespace,
        limit=limit,
        offset=offset,
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": incidents,
    }


@router.get("/{incident_id}",response_model=IncidentResponse)
def get_incident(incident_id: uuid.UUID,db: Session = Depends(get_db)):
    service = IncidentQueryService(db)

    incident = service.get_incident(incident_id)

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    return incident
