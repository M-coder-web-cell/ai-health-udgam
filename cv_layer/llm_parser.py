import json
import os
from dotenv import load_dotenv
from google import genai  # Corrected import
from pydantic import BaseModel

# Load env
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not set")

# 1. Initialize the new GenAI Client
client = genai.Client(api_key=GOOGLE_API_KEY)

SYSTEM_PROMPT = """
You are an information extraction system.
Extract the following fields from OCR text of a food package:
- product_name
- company_name
- IngredientList
- NutritionFacts
- MarketingClaims

Rules:
- Output ONLY valid JSON.
- If a field is missing, return empty string.
"""

def parse_with_gemini(ocr_text: str) -> dict:
    # 2. Use the new models.generate_content syntax
    response = client.models.generate_content(
        model="gemini-flash-lite-latest", # Updated to a current flash-lite version
        contents=f"{SYSTEM_PROMPT}\n\nOCR Text:\n{ocr_text}",
        config={
            "temperature": 0.0,
            "response_mime_type": "application/json"
        }
    )

    try:
        # In the new SDK, response.text is directly accessible
        return json.loads(response.text)
    except json.JSONDecodeError:
        # Fallback if JSON is wrapped in markdown
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)

