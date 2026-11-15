
import html
import logging

import httpx

from app.config import settings
from app.notifications.telegram.client import TelegramClient
from app.notifications.telegram.keyboards import IncidentKeyboard
from app.schemas.diagnosis_analysis import DiagnosisAnalysis


logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.timeout = settings.telegram_timeout_seconds

        self.telegram = TelegramClient(
            bot_token=self.bot_token,
            timeout_seconds=self.timeout,
        )

    @staticmethod
    def _escape(value) -> str:
        if value is None:
            return "N/A"

        return html.escape(str(value), quote=False)

    def _build_message(self, analysis: DiagnosisAnalysis) -> str:
        incident = analysis.context.incident
        diagnosis = analysis.diagnosis
        ai = analysis.ai_diagnosis

        severity = self._escape(
            (diagnosis.severity or incident.severity or "unknown").upper()
        )

        lines = [
            "🚨 <b>AI INCIDENT DIAGNOSIS</b>",
            "",
            f"<b>Incident:</b> {self._escape(incident.alert_name)}",
            f"<b>Severity:</b> {severity}",
            f"<b>Namespace:</b> {self._escape(incident.namespace)}",
            f"<b>Pod:</b> {self._escape(incident.pod)}",
            f"<b>Status:</b> {self._escape(incident.status)}",
            f"<b>Incident ID:</b> <code>{self._escape(incident.id)}</code>",
            "",
            "📋 <b>RULE-BASED DIAGNOSIS</b>",
            f"<b>Result:</b> {self._escape(diagnosis.status)}",
            f"<b>Probable cause:</b> {self._escape(diagnosis.probable_cause)}",
            f"<b>Confidence:</b> {diagnosis.confidence:.0%}",
            f"<b>Summary:</b> {self._escape(diagnosis.summary)}",
        ]

        if diagnosis.findings:
            lines.extend(["", "🔎 <b>FINDINGS</b>"])

            for finding in diagnosis.findings[:5]:
                lines.append(
                    f"• [{self._escape(finding.severity.upper())}] "
                    f"{self._escape(finding.title)}"
                )
                lines.append(
                    f"  {self._escape(finding.description)}"
                )

        lines.extend(["", "🤖 <b>GEMINI ANALYSIS</b>"])

        if ai is None or ai.status == "unavailable":
            lines.append(
                "AI analysis is currently unavailable."
            )
        else:
            lines.extend([
                f"<b>Probable cause:</b> "
                f"{self._escape(ai.probable_cause)}",
                f"<b>Confidence:</b> "
                f"{ai.confidence:.0%}" if ai.confidence is not None
                else "<b>Confidence:</b> N/A",
                f"<b>Explanation:</b> "
                f"{self._escape(ai.explanation)}",
            ])

            if ai.supporting_evidence:
                lines.extend(["", "<b>Supporting evidence:</b>"])

                for item in ai.supporting_evidence[:8]:
                    lines.append(f"• {self._escape(item)}")

            if ai.investigation_steps:
                lines.extend(["", "🛠 <b>INVESTIGATION STEPS</b>"])

                for index, step in enumerate(
                    ai.investigation_steps[:5],
                    1,
                ):
                    lines.append(
                        f"{index}. <code>{self._escape(step)}</code>"
                    )

        lines.extend(["", "📡 <b>EVIDENCE COLLECTION</b>"])

        statuses = analysis.context.collection_status

        lines.extend([
            f"• Prometheus: {self._escape(statuses.prometheus)}",
            f"• Loki: {self._escape(statuses.loki)}",
            f"• Kubernetes: {self._escape(statuses.kubernetes)}",
            "",
            "<i>AI-generated analysis. Human verification required.</i>",
        ])

        message = "\n".join(lines)

        if len(message) > 3900:
            message = "\n".join([
                "🚨 <b>AI INCIDENT DIAGNOSIS</b>",
                "",
                f"<b>Incident:</b> {self._escape(incident.alert_name)}",
                f"<b>Severity:</b> {severity}",
                f"<b>Namespace:</b> {self._escape(incident.namespace)}",
                f"<b>Pod:</b> {self._escape(incident.pod)}",
                f"<b>Incident ID:</b> "
                f"<code>{self._escape(incident.id)}</code>",
                "",
                "<i>Detailed diagnosis omitted because the message "
                "exceeded Telegram's message limit.</i>",
            ])

        return message

    async def send_diagnosis(
        self,
        analysis: DiagnosisAnalysis,
    ) -> None:
        if not settings.telegram_enabled:
            logger.info("Telegram notifications are disabled")
            return

        if not self.bot_token or not self.chat_id:
            raise ValueError(
                "Telegram bot token or chat ID is not configured"
            )

        keyboard = IncidentKeyboard.controls(
            analysis.context.incident.id
        )

        async with httpx.AsyncClient(
            timeout=self.timeout,
        ) as client:
            await self.telegram.send_message(
                client=client,
                chat_id=self.chat_id,
                text=self._build_message(analysis),
                reply_markup=keyboard,
            )

        logger.info(
            "Telegram notification sent for incident %s",
            analysis.context.incident.id,
        )
