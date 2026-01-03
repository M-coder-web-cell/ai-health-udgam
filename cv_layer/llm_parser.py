import json
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load env
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not set")

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)

SYSTEM_PROMPT = """
You are an information extraction system.

Extract the following fields from OCR text of a food package:
- product_name
- company_name
- IngredientList
- NutritionFacts
- MarketingClaims

Rules:
- Use ONLY the provided text
- Do NOT infer or guess
- If a field is missing, return empty string
- Output ONLY valid JSON
"""

model = genai.GenerativeModel(
    model_name="gemini-flash-lite-latest",
    generation_config={
        "temperature": 0.0,
        "response_mime_type": "application/json"
    }
)

def parse_with_gemini(ocr_text: str) -> dict:
    response = model.generate_content(
        f"{SYSTEM_PROMPT}\n\nOCR Text:\n{ocr_text}"
    )

    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON from Gemini:\n{response.text}")
