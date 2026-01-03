SYSTEM_PROMPT = """
Based on product and consumer persona:
- infer concerns
- risk level
- usage intent

Output valid JSON only.
"""

def infer_intent(product_json, persona):
    payload = {
        "product": product_json,
        "persona": persona
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
