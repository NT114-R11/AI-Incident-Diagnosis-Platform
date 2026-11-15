import logging
import httpx


logger = logging.getLogger(__name__)


class TelegramClient:
    def __init__(self, bot_token: str, timeout_seconds: float = 10.0):
        if not bot_token:
            raise ValueError("Telegram bot token is not configured")

        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.timeout = httpx.Timeout(
            timeout_seconds,
            connect=10.0,
        )

    async def call(self, client: httpx.AsyncClient, method: str, payload: dict | None = None ) -> dict:
        response = await client.post(
            f"{self.base_url}/{method}",
            json=payload or {},
        )
        response.raise_for_status()

        result = response.json()

        if not result.get("ok"):
            raise RuntimeError(
                f"Telegram API error: {result}"
            )

        return result

    async def answer_callback(self, client: httpx.AsyncClient, callback_id: str, text: str = "Processing...") -> dict:
        return await self.call(
            client,
            "answerCallbackQuery",
            {
                "callback_query_id": callback_id,
                "text": text,
            },
        )

    async def send_message(self, client: httpx.AsyncClient, chat_id: int, text: str, reply_markup: dict | None = None) -> dict:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        return await self.call(
            client,
            "sendMessage",
            payload,
        )

    async def edit_message(self, client: httpx.AsyncClient, chat_id: int, message_id: int, text: str, reply_markup: dict | None = None) -> dict:
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        return await self.call(
            client,
            "editMessageText",
            payload,
        )

    async def delete_webhook(self, client: httpx.AsyncClient, drop_pending_updates: bool = False) -> dict:
        return await self.call(
            client,
            "deleteWebhook",
            {
                "drop_pending_updates": drop_pending_updates,
            },
        )

    async def get_updates(self, client: httpx.AsyncClient, offset: int | None = None, timeout: int = 25, allowed_updates: list[str] | None = None) -> dict:
        payload = {
            "timeout": timeout,
            "allowed_updates": (
                allowed_updates
                if allowed_updates is not None
                else ["message", "callback_query"]
            ),
        }

        if offset is not None:
            payload["offset"] = offset

        return await self.call(
            client,
            "getUpdates",
            payload,
        )
