import json
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

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

def parse_with_llm(ocr_text: str) -> dict:
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": ocr_text}
        ],
        temperature=0
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("LLM did not return valid JSON")
