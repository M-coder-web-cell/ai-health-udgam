from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()

class llm:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    def ask(self, prompt: str) -> str:
        response = self.client.models.generate_content(
        model=self.model_name,
        contents=prompt)

        return response.text

    def askwithsearch(self, prompt: str) -> str:
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        config = types.GenerateContentConfig(
        tools=[grounding_tool]
        )
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config
        )
        return response.candidates[0].content