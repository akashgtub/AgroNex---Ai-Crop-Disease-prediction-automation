class AIAssistant:
    def answer(self, question: str, language: str, context: dict):
        if language == "ta":
            return "இது ஒரு மாதிரி பதில். (This is a mock response)."
        return "This is a mock response from AgroNex AI. You asked: " + question
