
import logging
import math
import uuid

import httpx

from app.config import settings
from app.database.connection import SessionLocal
from app.notifications.telegram.client import TelegramClient
from app.notifications.telegram.formatters import (
    DashboardFormatter,
    IncidentFormatter,
)
from app.notifications.telegram.keyboards import (
    IncidentKeyboard,
    MainMenuKeyboard,
)
from app.services.incident_query_service import IncidentQueryService


logger = logging.getLogger(__name__)


class CommandHandler:
    PAGE_SIZE = 5

    def __init__(
        self,
        telegram: TelegramClient,
        admin_ids: set[int] | None = None,
    ):
        self.telegram = telegram
        self.admin_ids = (
            admin_ids
            if admin_ids is not None
            else settings.telegram_admin_id_list
        )

    def _is_admin(self, message: dict) -> bool:
        user_id = message.get("from", {}).get("id")
        return user_id in self.admin_ids

    async def _send(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
    ):
        return await self.telegram.send_message(
            client=client,
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
        )

    async def handle(
        self,
        client: httpx.AsyncClient,
        message: dict,
    ):
        chat_id = message.get("chat", {}).get("id")
        text = (message.get("text") or "").strip()

        if chat_id is None or not text:
            return

        command, _, argument = text.partition(" ")
        command = command.split("@", 1)[0].lower()
        argument = argument.strip()

        # Support Reply Keyboard buttons.
        aliases = {
            "📋 incidents": "/incidents",
            "📊 summary": "/summary",
            "❓ help": "/help",
        }
        command = aliases.get(text.lower(), command)

        if command in {"/start", "/help"}:
            await self._show_help(client, chat_id)
            return

        if not self._is_admin(message):
            await self._send(
                client,
                chat_id,
                "⛔ You are not authorized to use this command.",
            )
            return

        if command == "/incidents":
            await self._show_incidents(
                client,
                chat_id,
                page=1,
            )
            return

        if command == "/summary":
            await self._show_summary(client, chat_id)
            return

        if command == "/incident":
            await self._show_incident(
                client,
                chat_id,
                argument,
            )
            return

        await self._send(
            client,
            chat_id,
            "Unknown command. Use /help to see available commands.",
            MainMenuKeyboard.build(),
        )

    async def _show_help(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
    ):
        message = "\n".join([
            "🤖 <b>AI INCIDENT DIAGNOSIS BOT</b>",
            "",
            "Available commands:",
            "",
            "/start — Open the main menu",
            "/help — Show this help message",
            "/incidents — List active incidents",
            "/summary — Show incident statistics",
            "/incident ID — View incident details",
            "",
            "Use the menu buttons below to navigate.",
        ])

        await self._send(
            client,
            chat_id,
            message,
            MainMenuKeyboard.build(),
        )

    async def _show_incidents(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        page: int,
    ):
        page = max(1, page)
        offset = (page - 1) * self.PAGE_SIZE

        db = SessionLocal()

        try:
            query_service = IncidentQueryService(db)

            # Fetch enough records from both active statuses
            # to construct one globally sorted page.
            fetch_limit = offset + self.PAGE_SIZE

            open_items, open_total = query_service.list_incidents(
                status="open",
                limit=fetch_limit,
                offset=0,
            )

            acknowledged_items, acknowledged_total = (
                query_service.list_incidents(
                    status="acknowledged",
                    limit=fetch_limit,
                    offset=0,
                )
            )

            incidents = open_items + acknowledged_items
            incidents.sort(
                key=lambda incident: incident.created_at,
                reverse=True,
            )

            total = open_total + acknowledged_total
            total_pages = max(
                1,
                math.ceil(total / self.PAGE_SIZE),
            )

            # Clamp page if the result set has changed.
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
                page=page,
                total_pages=total_pages,
            )

            await self._send(
                client,
                chat_id,
                text,
                keyboard,
            )

        finally:
            db.close()

    async def _show_summary(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
    ):
        db = SessionLocal()

        try:
            summary = IncidentQueryService(db).get_summary()
            text = DashboardFormatter.format_summary(summary)

            await self._send(
                client,
                chat_id,
                text,
                MainMenuKeyboard.build(),
            )

        finally:
            db.close()

    async def _show_incident(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        incident_id_raw: str,
    ):
        try:
            incident_id = uuid.UUID(incident_id_raw)
        except (ValueError, TypeError, AttributeError):
            await self._send(
                client,
                chat_id,
                "⚠️ Invalid incident ID. Please provide a valid UUID.",
            )
            return

        db = SessionLocal()

        try:
            incident = IncidentQueryService(db).get_incident(
                incident_id
            )

            if incident is None:
                await self._send(
                    client,
                    chat_id,
                    "Incident not found.",
                )
                return

            text = IncidentFormatter.format(incident)

            await self._send(
                client,
                chat_id,
                text,
                IncidentKeyboard.controls(incident.id),
            )

        finally:
            db.close()
