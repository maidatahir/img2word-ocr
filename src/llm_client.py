import google.generativeai as genai

class GeminiClient:
    def __init__(self, apiKey):
        self.apiKey = apiKey
        if apiKey:
            genai.configure(api_key=apiKey)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def isActive(self):
        return self.model is not None

    def refineOcrText(self, rawText):
        if not self.isActive():
            return rawText
        prompt = (
            "You are a professional document reconstruction agent. Your task is to transform raw, noisy OCR output into a perfectly formatted, grammatically correct document.\n\n"
            "RULES:\n"
            "1. Fix all character misinterpretations (e.g., 'Tnformation' -> 'Information', '1' -> 'I').\n"
            "2. Correct sentence structure and grammar while preserving the original meaning.\n"
            "3. Remove obvious OCR noise (stray symbols like ~~ or | if they don't belong).\n"
            "4. Organize the text into logical paragraphs if it looks like a continuous block.\n"
            "5. OUTPUT ONLY THE REFINED TEXT. DO NOT EXPLAIN YOUR CHANGES.\n\n"
            f"RAW NOISY TEXT:\n{rawText}\n\nREFINED PROFESSIONAL TEXT:"
        )
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except:
            return rawText

    def getChatResponse(self, userQuery, documentContext=None):
        if not self.isActive():
            return "I need an API key to provide intelligent responses. Please add one in settings."
        contextStr = f"\nDOCUMENT CONTEXT:\n{documentContext}\n" if documentContext else ""
        prompt = (
            "You are an AI Assistant for an Image-to-Word converter. "
            "Help users understand their documents. Keep responses concise.\n"
            f"{contextStr}"
            f"USER QUERY: {userQuery}"
        )
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error connecting to Gemini: {str(e)}"
