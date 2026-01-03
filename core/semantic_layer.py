import openai, json, os

openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """
You analyze product data and infer:
- product_type
- subcategory
- primary_use
- key_attributes

Be generic. Output valid JSON only.
"""

def semantic_understanding(product_json):
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(product_json)}
        ],
        temperature=0.2
    )
    return json.loads(response.choices[0].message.content)
