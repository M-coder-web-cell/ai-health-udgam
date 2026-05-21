import json
import time
import os
from kafka import KafkaConsumer
from google import genai
from google.genai import types
from dotenv import load_dotenv
from knowledge_store.graph_manager import HealthGraphManager

load_dotenv()

# System prompt for LLM-based KG extraction
KG_EXTRACT_PROMPT = """
You are a Clinical & Dietary Knowledge Graph Extraction Agent. Your task is to analyze user profile data, queries, and scanned product ingredients, and parse them into structured entity relationships for a personalized health knowledge graph.

**Current Input Payload**:
- **User Node ID**: "{user_id}"
- **User Query**: "{user_query}"
- **User Profile Context**: {user_profile}
- **Product Context (OCR)**: {product_json}

Your goal is to extract ALL valid relationships between the entities.
Allowed Node Types: user, condition, allergen, ingredient, goal, product
Allowed Relationship Types:
- (user) -[HAS_CONDITION]-> (condition)
- (user) -[HAS_ALLERGY]-> (allergen)
- (user) -[HAS_GOAL]-> (goal)
- (condition) -[RESTRICTS]-> (ingredient)
- (condition) -[CONTRAINDICATED_WITH]-> (ingredient)
- (allergen) -[FOUND_IN]-> (ingredient)
- (product) -[CONTAINS]-> (ingredient)
- (goal) -[AVOIDS]-> (ingredient)
- (goal) -[BENEFITS_FROM]-> (ingredient)

Output strictly in a JSON dictionary matching this structure:
{{
  "relationships": [
    {{
      "source_id": "Entity Name (e.g. Diabetes, Gluten, Sugar, weight loss)",
      "source_type": "user" | "condition" | "allergen" | "ingredient" | "goal" | "product",
      "target_id": "Target Entity Name",
      "target_type": "user" | "condition" | "allergen" | "ingredient" | "goal" | "product",
      "relationship_type": "HAS_CONDITION" | "HAS_ALLERGY" | "HAS_GOAL" | "RESTRICTS" | "CONTRAINDICATED_WITH" | "FOUND_IN" | "CONTAINS" | "AVOIDS" | "BENEFITS_FROM"
    }}
  ]
}}

**Strict Extraction Guidelines**:
1. **User Profile**: Extract any explicit allergies, conditions, or goals into relationships starting from the user node (ID "{user_id}").
   - E.g. User has allergy to peanuts: source_id="{user_id}", source_type="user", target_id="peanut allergy", target_type="allergen", relationship_type="HAS_ALLERGY".
2. **Clinical Mapping**: Map clinical common sense links between conditions/allergies and ingredients based on the query or general medicine.
   - E.g. Diabetes -> RESTRICTS -> sugar
   - E.g. Hypertension -> RESTRICTS -> sodium
   - E.g. Celiac disease -> RESTRICTS -> gluten
3. **Product Ingredients**: If a product and its ingredient list are provided, extract (product) -[CONTAINS]-> (ingredient) edges.
4. **Normalize Names**: Convert all non-user entities (conditions, ingredients, allergies, goals) to lowercase, clean, standardized names (e.g., "high fructose corn syrup" instead of "High-Fructose Corn Syrup!").
5. Return ONLY valid, parseable JSON. Do not write markdown blocks or any explanations outside the JSON payload.
"""

class KGBuilderConsumer:
    def __init__(self, bootstrap_servers=['localhost:9092'], topic='user-queries'):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.graph_manager = HealthGraphManager()
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    def run_once(self):
        print(f"[KGConsumer] Connecting to Kafka at {self.bootstrap_servers}...")
        consumer = None
        while not consumer:
            try:
                consumer = KafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id='kg-builder-group',
                    auto_offset_reset='latest',
                    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
                )
                print(f"[KGConsumer] Connected successfully to topic '{self.topic}'.")
            except Exception as e:
                print(f"[KGConsumer] Connection failed: {e}. Retrying in 5s...")
                time.sleep(5)

        try:
            msg_pack = consumer.poll(timeout_ms=1000)
            for topic_partition, messages in msg_pack.items():
                for message in messages:
                    payload = message.value
                    print(f"[KGConsumer] Received message: {payload.get('session_id')}")
                    self._process_message(payload)
        finally:
            consumer.close()

    def run_forever(self):
        while True:
            try:
                self.run_once()
                time.sleep(1)
            except KeyboardInterrupt:
                print("[KGConsumer] Stopping on KeyboardInterrupt.")
                break
            except Exception as e:
                print(f"[KGConsumer] Error in consume loop: {e}")
                time.sleep(2)

    def _process_message(self, payload):
        try:
            user_id = payload.get("user_email") or "Guest"
            user_query = payload.get("user_query") or ""
            user_profile = payload.get("user_profile") or {"allergies": [], "conditions": [], "goals": []}
            product_json = payload.get("product_json") or {}

            # Format the prompt
            prompt = KG_EXTRACT_PROMPT.format(
                user_id=user_id,
                user_query=user_query,
                user_profile=json.dumps(user_profile),
                product_json=json.dumps(product_json)
            )

            # Generate extraction using Gemini
            response = self.client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )

            result_text = response.text.replace("```json", "").replace("```", "").strip()
            result_dict = json.loads(result_text)

            relationships = result_dict.get("relationships", [])
            print(f"[KGConsumer] Parsed {len(relationships)} relationships from LLM.")

            # Load into Graph
            for rel in relationships:
                source_id = rel.get("source_id")
                source_type = rel.get("source_type")
                target_id = rel.get("target_id")
                target_type = rel.get("target_type")
                rel_type = rel.get("relationship_type")

                if not all([source_id, source_type, target_id, target_type, rel_type]):
                    continue

                # Add to NetworkX graph via manager
                self.graph_manager.add_relationship(
                    source_id=source_id,
                    source_type=source_type,
                    target_id=target_id,
                    target_type=target_type,
                    rel_type=rel_type
                )
            
            print(f"[KGConsumer] Successfully processed KG extraction for {user_id}.")

        except Exception as e:
            print(f"[KGConsumer] Error processing message: {e}")

if __name__ == "__main__":
    consumer = KGBuilderConsumer()
    consumer.run_forever()
