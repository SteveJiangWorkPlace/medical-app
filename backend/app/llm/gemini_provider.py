from google import genai
from google.genai import types

from app.llm.base import LLMProvider


class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, temperature: float = 0) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def generate_json(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                response_mime_type="application/json",
            ),
        )
        return response.text or "{}"

    def generate_text(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
            ),
        )
        return response.text or ""
