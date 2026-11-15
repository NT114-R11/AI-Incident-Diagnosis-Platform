import html
import json


class EvidenceFormatter:
    MESSAGE_LIMIT = 3800
    CONTENT_LIMIT = 3000

    SOURCES = (
        "kubernetes",
        "prometheus",
        "loki",
    )

    @staticmethod
    def _serialize(evidence: dict) -> str:
        return json.dumps(
            evidence,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    @staticmethod
    def _escape(value) -> str:
        return html.escape(str(value or "N/A"))

    def format(self, context) -> list[str]:
        messages = []

        header = "\n".join([
            "📊 <b>INCIDENT EVIDENCE</b>",
            "",
            f"<b>Incident:</b> "
            f"{self._escape(context.incident.alert_name)}",
            f"<b>Namespace:</b> "
            f"{self._escape(context.incident.namespace)}",
            f"<b>Pod:</b> "
            f"{self._escape(context.incident.pod)}",
            f"<b>Collected at:</b> "
            f"{self._escape(context.collected_at)}",
            "",
        ])

        messages.append(header)

        for source in self.SOURCES:
            evidence = context.evidence.get(source, {})

            status = getattr(
                context.collection_status,
                source,
                "unknown",
            )

            if hasattr(status, "value"):
                status = status.value

            serialized = self._serialize(evidence)

            # Keep every message's HTML tags balanced.
            chunks = [
                serialized[index:index + self.CONTENT_LIMIT]
                for index in range(
                    0,
                    len(serialized),
                    self.CONTENT_LIMIT,
                )
            ] or ["{}"]

            for index, chunk in enumerate(chunks):
                part_label = (
                    f" (part {index + 1}/{len(chunks)})"
                    if len(chunks) > 1
                    else ""
                )

                section = "\n".join([
                    f"🔹 <b>{source.upper()} — "
                    f"{self._escape(status)}"
                    f"{part_label}</b>",
                    f"<pre>{html.escape(chunk)}</pre>",
                ])

                messages.append(section)

        return messages
