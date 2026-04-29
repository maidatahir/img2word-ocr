import google.generativeai as genai
import os
import json

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
            "You are an expert document digitizer. Below is raw text extracted from an image via OCR. "
            "Your goal is to fix any character misinterpretations (especially in scientific or technical terms), "
            "correct grammatical errors, and ensure the structure makes sense. "
            "Maintain the original meaning and tone. Do not add conversational filler.\n\n"
            f"RAW OCR TEXT:\n{rawText}\n\n"
            "REFINED TEXT:"
        )
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return rawText

    def getChatResponse(self, userQuery, documentContext=None):
        if not self.isActive():
            return "I need an API key to provide intelligent responses. Please add one in settings."

        contextStr = f"\nDOCUMENT CONTEXT:\n{documentContext}\n" if documentContext else ""
        
        prompt = (
            "You are an AI Assistant for an Image-to-Word converter. "
            "You help users understand their documents and provide technical assistance. "
            "Keep your responses concise and helpful.\n"
            f"{contextStr}"
            f"USER QUERY: {userQuery}"
        )

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error connecting to Gemini: {str(e)}"
