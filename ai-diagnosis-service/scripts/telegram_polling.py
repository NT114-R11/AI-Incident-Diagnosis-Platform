
import asyncio
import logging

import httpx

from app.config import settings
from app.notifications.telegram.client import TelegramClient
from app.notifications.telegram.handlers import (
    CallbackHandler,
    CommandHandler,
)


logger = logging.getLogger(__name__)

POLLING_TIMEOUT = 25
RETRY_DELAY = 5


class TelegramPolling:
    def __init__(self):
        self.telegram = TelegramClient(
            bot_token=settings.telegram_bot_token,
            timeout_seconds=settings.telegram_timeout_seconds,
        )

        self.admin_ids = settings.telegram_admin_id_list

        self.command_handler = CommandHandler(
            telegram=self.telegram,
            admin_ids=self.admin_ids,
        )

        self.callback_handler = CallbackHandler(
            telegram=self.telegram,
            admin_ids=self.admin_ids,
        )

    async def _process_update(
        self,
        client: httpx.AsyncClient,
        update: dict,
    ):
        message = update.get("message")
        callback = update.get("callback_query")

        if message:
            await self.command_handler.handle(
                client,
                message,
            )
            return

        if callback:
            await self.callback_handler.handle(
                client,
                callback,
            )

    async def run(self):
        if not settings.telegram_bot_token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is not configured"
            )

        if not self.admin_ids:
            raise ValueError(
                "TELEGRAM_ADMIN_IDS is not configured"
            )

        timeout = httpx.Timeout(
            40.0,
            connect=10.0,
        )

        async with httpx.AsyncClient(
            timeout=timeout,
        ) as client:

            # Long polling and webhook cannot run simultaneously.
            await self.telegram.delete_webhook(
                client,
                drop_pending_updates=False,
            )

            offset = None

            logger.info("Telegram polling started")

            while True:
                try:
                    result = await self.telegram.get_updates(
                        client=client,
                        offset=offset,
                        timeout=POLLING_TIMEOUT,
                        allowed_updates=[
                            "message",
                            "callback_query",
                        ],
                    )

                    updates = result.get("result", [])

                    for update in updates:
                        # Advance offset so the next getUpdates call
                        # acknowledges this update to Telegram.
                        offset = update["update_id"] + 1

                        try:
                            await self._process_update(
                                client,
                                update,
                            )

                        except asyncio.CancelledError:
                            raise

                        except Exception:
                            logger.exception(
                                "Failed to process Telegram update %s",
                                update.get("update_id"),
                            )

                except asyncio.CancelledError:
                    logger.info("Telegram polling stopped")
                    raise

                except Exception:
                    logger.exception(
                        "Telegram polling failed; retrying in %s seconds",
                        RETRY_DELAY,
                    )

                    await asyncio.sleep(RETRY_DELAY)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s: %(message)s"
        ),
    )

    polling = TelegramPolling()
    await polling.run()


if __name__ == "__main__":
    asyncio.run(main())
