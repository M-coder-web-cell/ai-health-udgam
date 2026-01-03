"""
Central orchestration pipeline.

This module:
- Takes product JSON as input
- Calls each intelligence layer in sequence
- Returns a unified intelligence output
"""

from semantic_layer import semantic_understanding
from persona_layer import infer_persona
from intent_layer import infer_intent
from recommendation_layer import recommend_actions


def intelligence_pipeline(product_json: dict) -> dict:
    """
    Runs the full intelligence pipeline.

    Args:
        product_json (dict): Extracted product data

    Returns:
        dict: Unified intelligence output
    """

    # 1️⃣ Understand the product semantically
    semantic = semantic_understanding(product_json)

    # 2️⃣ Infer likely consumer persona
    persona = infer_persona(product_json, semantic)

    # 3️⃣ Infer intent, concerns, and risk
    intent = infer_intent(product_json, persona)

    # 4️⃣ Generate recommendations & next actions
    actions = recommend_actions(product_json, persona, intent)

    return {
        "product": product_json,
        "semantic_understanding": semantic,
        "consumer_persona": persona,
        "intent_analysis": intent,
        "user_output": actions
    }


if __name__ == "__main__":
    # Example test input
    sample_product = {
        "product_name": "Organic Raw Honey",
        "company_name": "NatureFarm",
        "IngredientList": "Honey (100%)",
        "NutritionFacts": "Energy 304kcal, Sugars 82g",
        "MarketingClaims": "100% Natural, No Added Sugar"
    }

    output = intelligence_pipeline(sample_product)
    print(output)
