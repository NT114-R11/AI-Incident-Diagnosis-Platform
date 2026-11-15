
import html
import logging
import uuid

import httpx

from app.database.connection import SessionLocal
from app.notifications.telegram.client import TelegramClient
from app.notifications.telegram.formatters import (
    DashboardFormatter,
    EvidenceFormatter,
    IncidentFormatter,
)
from app.notifications.telegram.keyboards import (
    IncidentKeyboard,
)
from app.services.incident_context_service import (
    IncidentContextService,
)
from app.services.incident_query_service import (
    IncidentQueryService,
)
from app.services.incident_service import IncidentService


logger = logging.getLogger(__name__)


class CallbackHandler:
    PAGE_SIZE = 5

    def __init__(
        self,
        telegram: TelegramClient,
        admin_ids: set[int],
    ):
        self.telegram = telegram
        self.admin_ids = admin_ids
        self.evidence_formatter = EvidenceFormatter()

    async def _answer(
        self,
        client: httpx.AsyncClient,
        callback_id: str,
        text: str = "Processing...",
    ):
        return await self.telegram.answer_callback(
            client,
            callback_id,
            text,
        )

    async def _send(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
    ):
        return await self.telegram.send_message(
            client,
            chat_id,
            text,
            reply_markup,
        )

    async def _edit(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: dict | None = None,
    ):
        return await self.telegram.edit_message(
            client,
            chat_id,
            message_id,
            text,
            reply_markup,
        )

    async def handle(
        self,
        client: httpx.AsyncClient,
        callback: dict,
    ):
        callback_id = callback["id"]
        user_id = callback.get("from", {}).get("id")

        message = callback.get("message") or {}
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")

        if user_id not in self.admin_ids:
            await self._answer(
                client,
                callback_id,
                "You are not authorized.",
            )
            return

        data = callback.get("data", "")
        action, separator, argument = data.partition(":")

        # Acknowledge immediately. Evidence collection and DB
        # operations must not delay Telegram callback response.
        callback_text = (
            "Collecting evidence..."
            if action == "evidence"
            else "Processing..."
        )

        try:
            await self._answer(
                client,
                callback_id,
                callback_text,
            )
        except Exception:
            logger.exception(
                "Failed to acknowledge Telegram callback"
            )
            return

        if chat_id is None:
            return

        try:
            if action == "incidents_page":
                page = int(argument) if separator else 1

                await self._show_incidents(
                    client,
                    chat_id,
                    message_id,
                    page,
                )
                return

            if action == "incidents_refresh":
                await self._show_incidents(
                    client,
                    chat_id,
                    message_id,
                    1,
                )
                return

            if action in {
                "resolve_confirm",
                "resolve_execute",
                "resolve_cancel",
                "detail",
                "evidence",
                "ack",
                "investigate",
            }:
                incident_id = uuid.UUID(argument)
            else:
                await self._send(
                    client,
                    chat_id,
                    "⚠️ Unknown action.",
                )
                return

            if action == "resolve_confirm":
                await self._confirm_resolve(
                    client,
                    chat_id,
                    incident_id,
                )
                return

            if action == "resolve_cancel":
                await self._send(
                    client,
                    chat_id,
                    "❌ Resolve operation cancelled.",
                )
                return

            if action == "investigate":
                await self._send(
                    client,
                    chat_id,
                    "🔍 Further investigation workflow "
                    "has not been implemented yet.",
                )
                return

            await self._handle_incident_action(
                client,
                chat_id,
                incident_id,
                action,
            )

        except (ValueError, TypeError):
            logger.warning(
                "Invalid Telegram callback data: %s",
                data,
            )
            await self._send(
                client,
                chat_id,
                "⚠️ Invalid callback data or incident ID.",
            )

        except Exception:
            logger.exception(
                "Failed to process Telegram callback: %s",
                action,
            )

            try:
                await self._send(
                    client,
                    chat_id,
                    "❌ An internal error occurred "
                    "while processing your request.",
                )
            except Exception:
                logger.exception(
                    "Failed to send callback error message"
                )

    async def _handle_incident_action(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        incident_id: uuid.UUID,
        action: str,
    ):
        if action == "evidence":
            await self._show_evidence(
                client,
                chat_id,
                incident_id,
            )
            return

        db = SessionLocal()

        try:
            if action == "detail":
                incident = IncidentQueryService(
                    db
                ).get_incident(incident_id)

                if incident is None:
                    result = "Incident not found."
                else:
                    result = IncidentFormatter.format(incident)
                    keyboard = IncidentKeyboard.controls(
                        incident.id
                    )

                    await self._send(
                        client,
                        chat_id,
                        result,
                        keyboard,
                    )
                    return

            elif action == "ack":
                incident = IncidentService(
                    db
                ).acknowledge_incident(incident_id)

                if incident is None:
                    result = "Incident not found."
                else:
                    result = (
                        f"✅ Incident <code>{incident.id}</code>\n"
                        f"Status: <b>"
                        f"{html.escape(incident.status)}</b>"
                    )

            elif action == "resolve_execute":
                incident = IncidentService(
                    db
                ).resolve_incident(incident_id)

                if incident is None:
                    result = "Incident not found."
                else:
                    result = (
                        f"🏁 Incident <code>{incident.id}</code>\n"
                        f"Status: <b>"
                        f"{html.escape(incident.status)}</b>"
                    )

            else:
                result = "Unsupported incident action."

            await self._send(
                client,
                chat_id,
                result,
            )

        finally:
            db.close()

    async def _show_evidence(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        incident_id: uuid.UUID,
    ):
        db = SessionLocal()

        try:
            incident = IncidentQueryService(
                db
            ).get_incident(incident_id)

            if incident is None:
                await self._send(
                    client,
                    chat_id,
                    "Incident not found.",
                )
                return

            context = await IncidentContextService().collect(
                incident
            )

            messages = self.evidence_formatter.format(context)

            for message in messages:
                await self._send(
                    client,
                    chat_id,
                    message,
                )

        finally:
            db.close()

    async def _confirm_resolve(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        incident_id: uuid.UUID,
    ):
        db = SessionLocal()

        try:
            incident = IncidentQueryService(
                db
            ).get_incident(incident_id)

            if incident is None:
                await self._send(
                    client,
                    chat_id,
                    "Incident not found.",
                )
                return

            if incident.status == "resolved":
                await self._send(
                    client,
                    chat_id,
                    "This incident is already resolved.",
                )
                return

            text = "\n".join([
                "⚠️ <b>CONFIRM INCIDENT RESOLUTION</b>",
                "",
                f"Alert: {html.escape(incident.alert_name or 'N/A')}",
                f"Status: <b>{html.escape(incident.status)}</b>",
                "",
                "Are you sure you want to resolve this incident?",
            ])

            await self._send(
                client,
                chat_id,
                text,
                IncidentKeyboard.resolve_confirmation(
                    incident.id
                ),
            )

        finally:
            db.close()

    async def _show_incidents(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        message_id: int | None,
        page: int,
    ):
        page = max(1, page)
        offset = (page - 1) * self.PAGE_SIZE
        db = SessionLocal()

        try:
            query = IncidentQueryService(db)
            fetch_limit = offset + self.PAGE_SIZE

            open_items, open_total = query.list_incidents(
                status="open",
                limit=fetch_limit,
                offset=0,
            )

            acknowledged_items, acknowledged_total = (
                query.list_incidents(
                    status="acknowledged",
                    limit=fetch_limit,
                    offset=0,
                )
            )

            incidents = open_items + acknowledged_items
            incidents.sort(
                key=lambda item: item.created_at,
                reverse=True,
            )

            total = open_total + acknowledged_total
            total_pages = max(
                1,
                (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE,
            )

            page = min(page, total_pages)
            offset = (page - 1) * self.PAGE_SIZE

            page_items = incidents[
                offset:offset + self.PAGE_SIZE
            ]

            text = DashboardFormatter.format_incidents(
                incidents=page_items,
                total=total,
                page=page,
                page_size=self.PAGE_SIZE,
            )

            keyboard = IncidentKeyboard.pagination(
                page,
                total_pages,
            )

            if message_id is not None:
                try:
                    await self._edit(
                        client,
                        chat_id,
                        message_id,
                        text,
                        keyboard,
                    )
                    return
                except httpx.HTTPStatusError:
                    logger.warning(
                        "Could not edit incident list; sending new message"
                    )

            await self._send(
                client,
                chat_id,
                text,
                keyboard,
            )

        finally:
            db.close()
