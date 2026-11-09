
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.alertmanager import AlertmanagerWebhook
from app.services.alert_processor import process_alertmanager_webhook


router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
)


@router.post("/alertmanager")
def receive_alertmanager_webhook(
    payload: AlertmanagerWebhook,
    db: Session = Depends(get_db),
):
    return process_alertmanager_webhook(payload, db)
