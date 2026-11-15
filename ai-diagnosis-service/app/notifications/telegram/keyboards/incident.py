
from uuid import UUID


class IncidentKeyboard:
    @staticmethod
    def controls(incident_id: UUID) -> dict:
        incident_id = str(incident_id)

        return {
            "inline_keyboard": [
                [
                    {
                        "text": "📋 View Details",
                        "callback_data": f"detail:{incident_id}",
                    },
                    {
                        "text": "📊 View Evidence",
                        "callback_data": f"evidence:{incident_id}",
                    },
                ],
                [
                    {
                        "text": "🔍 Investigate More",
                        "callback_data": f"investigate:{incident_id}",
                    },
                ],
                [
                    {
                        "text": "✅ Acknowledge",
                        "callback_data": f"ack:{incident_id}",
                    },
                    {
                        "text": "🏁 Resolve",
                        "callback_data": f"resolve_confirm:{incident_id}",
                    },
                ],
            ]
        }

    @staticmethod
    def resolve_confirmation(incident_id: UUID) -> dict:
        incident_id = str(incident_id)

        return {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Confirm Resolve",
                        "callback_data": f"resolve_execute:{incident_id}",
                    },
                    {
                        "text": "❌ Cancel",
                        "callback_data": f"resolve_cancel:{incident_id}",
                    },
                ]
            ]
        }

    @staticmethod
    def pagination(
        page: int,
        total_pages: int,
    ) -> dict:
        buttons = []

        if page > 1:
            buttons.append({
                "text": "⬅️ Previous",
                "callback_data": f"incidents_page:{page - 1}",
            })

        if page < total_pages:
            buttons.append({
                "text": "Next ➡️",
                "callback_data": f"incidents_page:{page + 1}",
            })

        rows = []

        if buttons:
            rows.append(buttons)

        rows.append([
            {
                "text": "🔄 Refresh",
                "callback_data": "incidents_refresh",
            }
        ])

        return {"inline_keyboard": rows}
