
class MainMenuKeyboard:
    @staticmethod
    def build() -> dict:
        return {
            "keyboard": [
                [
                    {"text": "📋 Incidents"},
                    {"text": "📊 Summary"},
                ],
                [
                    {"text": "❓ Help"},
                ],
            ],
            "resize_keyboard": True,
            "is_persistent": True,
        }
