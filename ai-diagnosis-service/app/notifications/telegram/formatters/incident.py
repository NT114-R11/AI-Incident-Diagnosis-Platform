import html


class IncidentFormatter:
    @staticmethod
    def format(incident) -> str:
        def safe(value):
            return html.escape(str(value or "N/A"))

        return "\n".join([
            "📋 <b>INCIDENT DETAILS</b>",
            "",
            f"<b>Alert:</b> {safe(incident.alert_name)}",
            f"<b>Severity:</b> {safe(incident.severity)}",
            f"<b>Status:</b> {safe(incident.status)}",
            f"<b>Namespace:</b> {safe(incident.namespace)}",
            f"<b>Pod:</b> {safe(incident.pod)}",
            f"<b>Summary:</b> {safe(incident.summary)}",
            "",
            f"<b>ID:</b> <code>{safe(incident.id)}</code>",
            f"<b>First seen:</b> {safe(incident.first_seen_at)}",
            f"<b>Last seen:</b> {safe(incident.last_seen_at)}",
            f"<b>Resolved at:</b> {safe(incident.resolved_at)}",
        ])
