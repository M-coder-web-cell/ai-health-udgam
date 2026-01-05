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
You are a Forensic OCR Analyst for food safety. 
Your task is to extract structured data from messy, noisy OCR text.

**OCR Text:**
{ocr_text}

**Instructions:**
1. **Aggressive Autocorrect:** The OCR text contains errors (e.g., "Miik" -> "Milk", "Peanui" -> "Peanut", "Sodiune" -> "Sodium"). You MUST correct these based on context.
2. **Nutrition Parsing:** Do NOT return the raw Nutrition text. Extract specific values into a dictionary (e.g., "Protein": "22g").
3. **Ingredient Extraction:** Look for keywords like "Ingredients:", "Contains:", or lists of food items. Extract them into a clean list.

**Output strictly in JSON:**
{{
  "product_name": "Inferred Name (or empty)",
  "company_name": "Inferred Company (or empty)",
  "IngredientList": ["Corrected Ingredient 1", "Corrected Ingredient 2"],
  "NutritionFacts": {{
    "Calories": "Value",
    "Protein": "Value",
    "Total Fat": "Value",
    "Total Sugars": "Value"
  }},
  "MarketingClaims": ["Claim 1", "Claim 2"]
}}
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

