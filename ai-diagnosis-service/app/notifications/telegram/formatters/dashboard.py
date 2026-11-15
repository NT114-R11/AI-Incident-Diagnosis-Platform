
import html


class DashboardFormatter:
    @staticmethod
    def _safe(value):
        return html.escape(str(value or "N/A"))

    @classmethod
    def format_incidents(
        cls,
        incidents: list,
        total: int,
        page: int,
        page_size: int,
    ) -> str:
        total_pages = max(
            1,
            (total + page_size - 1) // page_size,
        )

        lines = [
            "📋 <b>INCIDENT LIST</b>",
            "",
            f"Total: <b>{total}</b>",
            f"Page: <b>{page}/{total_pages}</b>",
            "",
        ]

        if not incidents:
            lines.append("No incidents found.")
            return "\n".join(lines)

        for index, incident in enumerate(incidents, start=1):
            lines.extend([
                f"<b>{index}. {cls._safe(incident.alert_name)}</b>",
                f"Severity: {cls._safe(incident.severity)}",
                f"Status: {cls._safe(incident.status)}",
                f"Namespace: {cls._safe(incident.namespace)}",
                f"Pod: {cls._safe(incident.pod)}",
                f"ID: <code>{cls._safe(incident.id)}</code>",
                "",
            ])

        return "\n".join(lines)

    @staticmethod
    def format_summary(summary: dict) -> str:
        def count(key):
            return summary.get(key, 0)

        return "\n".join([
            "📊 <b>INCIDENT SUMMARY</b>",
            "",
            f"Total: <b>{count('total')}</b>",
            "",
            "📌 <b>By status</b>",
            f"🔴 Open: <b>{count('open')}</b>",
            f"🟡 Acknowledged: "
            f"<b>{count('acknowledged')}</b>",
            f"🟢 Resolved: <b>{count('resolved')}</b>",
        ])
