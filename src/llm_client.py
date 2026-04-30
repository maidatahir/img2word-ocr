"""
Gemini AI Client Module
Encapsulates communication with Google's Generative AI (Gemini) 
for document refinement and conversational assistance.
"""

import google.generativeai as genai
import os
import json

class GeminiClient:
    """A high-level client for interacting with the Gemini 1.5 LLM."""
    
    def __init__(self, apiKey):
        """Initializes the Gemini model with the provided API key."""
        self.apiKey = apiKey
        if apiKey:
            genai.configure(api_key=apiKey)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def isActive(self):
        """Checks if the client has a valid model instance initialized."""
        return self.model is not None

    def refineOcrText(self, rawText):
        """
        Uses Gemini to perform semantic correction on raw OCR output.
        Fixes typos, improves grammar, and enhances structural flow.
        """
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
            # Generate the cleaned version of the text
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            # Fallback to original text if the API call fails
            return rawText

    def getChatResponse(self, userQuery, documentContext=None):
        """
        Generates a conversational response for the Agent Assistant.
        Provides context about the current document to improve answer relevance.
        """
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
