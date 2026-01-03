import openai, json, os

openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """
Generate:
- recommendations
- warnings
- follow_up_questions

Keep it practical.
Output JSON only.
"""

def recommend_actions(product_json, persona, intent):
    payload = {
        "product": product_json,
        "persona": persona,
        "intent": intent
    }

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload)}
        ],
        temperature=0.4
    )
    return json.loads(response.choices[0].message.content)
