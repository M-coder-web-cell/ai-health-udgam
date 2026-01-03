import openai, json, os

openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """
Infer the likely consumer persona(s) for this product.

Rules:
- Do NOT assume demographics unless implied
- Personas should describe mindset & priorities
- Output JSON only

Keys:
- consumer_persona (list)
- confidence (0-1)
"""

def infer_persona(product_json, semantic_info):
    payload = {
        "product": product_json,
        "semantic": semantic_info
    }

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload)}
        ],
        temperature=0.3
    )
    return json.loads(response.choices[0].message.content)
