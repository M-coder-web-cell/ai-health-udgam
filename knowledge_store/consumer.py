import json
import time
import os
import traceback
from kafka import KafkaConsumer
from kafka.errors import KafkaError
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
        self.consumer = None
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        self.client = genai.Client(api_key=api_key)
        
        print(f"\n[KGConsumer] ===== INITIALIZED =====")
        print(f"[KGConsumer] Topic: {self.topic}")
        print(f"[KGConsumer] Bootstrap Servers: {self.bootstrap_servers}")
        print(f"[KGConsumer] Group ID: kg-builder-group")
        print(f"[KGConsumer] Auto Offset Reset: earliest (CHANGED FROM latest)")
        print(f"[KGConsumer] ========================\n")
        self._init_consumer()

    def _init_consumer(self):
        """Initialize Kafka consumer with retry logic"""
        retry_count = 0
        max_retries = 10
        while retry_count < max_retries:
            try:
                print(f"[KGConsumer] Attempting connection to Kafka (attempt {retry_count + 1}/{max_retries})...")
                self.consumer = KafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id='kg-builder-group',
                    auto_offset_reset='earliest',  # CHANGED: from 'latest' to 'earliest'
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    session_timeout_ms=30000,
                    request_timeout_ms=60000
                )
                print(f"[KGConsumer] ✓ Connected successfully to Kafka.")
                print(f"[KGConsumer] Subscribed to topic: {self.topic}\n")
                return
            except KafkaError as ke:
                print(f"[KGConsumer] ✗ Kafka connection error: {ke}")
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = min(5 * retry_count, 30)
                    print(f"[KGConsumer] Retrying in {wait_time}s...\n")
                    time.sleep(wait_time)
            except Exception as e:
                print(f"[KGConsumer] ✗ Unexpected error during connection: {e}")
                traceback.print_exc()
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(5)
        
        raise RuntimeError(f"Failed to connect to Kafka after {max_retries} attempts")

    def run_once(self):
        """Single poll cycle - reuse persistent consumer connection"""
        if not self.consumer:
            raise RuntimeError("Consumer not initialized")
        
        try:
            print("[KGConsumer] Polling for messages (timeout: 5000ms)...")
            msg_pack = self.consumer.poll(timeout_ms=5000, max_records=10)
            
            if not msg_pack:
                print("[KGConsumer] No messages received in this poll cycle.")
                return
            
            message_count = sum(len(messages) for messages in msg_pack.values())
            print(f"[KGConsumer] ✓ Received {message_count} message(s)")
            
            for topic_partition, messages in msg_pack.items():
                print(f"[KGConsumer] Processing partition {topic_partition}...")
                for idx, message in enumerate(messages, 1):
                    try:
                        payload = message.value
                        session_id = payload.get('session_id')
                        user_email = payload.get('user_email')
                        print(f"[KGConsumer] [Message {idx}] session_id={session_id}, user={user_email}")
                        self._process_message(payload)
                    except Exception as msg_err:
                        print(f"[KGConsumer] ✗ Error processing message {idx}: {msg_err}")
                        traceback.print_exc()
        except KafkaError as ke:
            print(f"[KGConsumer] ✗ Kafka error during poll: {ke}")
            traceback.print_exc()
        except Exception as e:
            print(f"[KGConsumer] ✗ Unexpected error in run_once: {e}")
            traceback.print_exc()

    def run_forever(self):
        """Main loop - continuous polling with error recovery"""
        print("\n[KGConsumer] ===== STARTING CONSUMER LOOP =====")
        poll_count = 0
        try:
            while True:
                poll_count += 1
                print(f"\n[KGConsumer] === Poll Cycle {poll_count} ===")
                try:
                    self.run_once()
                    time.sleep(2)
                except KeyboardInterrupt:
                    print("\n[KGConsumer] Received KeyboardInterrupt. Shutting down...")
                    break
                except Exception as e:
                    print(f"[KGConsumer] ✗ Error in consume loop: {e}")
                    traceback.print_exc()
                    time.sleep(5)
        finally:
            self._cleanup()

    def _cleanup(self):
        """Clean shutdown"""
        print("\n[KGConsumer] Cleaning up...")
        if self.consumer:
            try:
                self.consumer.close()
                print("[KGConsumer] ✓ Consumer closed successfully")
            except Exception as e:
                print(f"[KGConsumer] ✗ Error closing consumer: {e}")

    def _process_message(self, payload):
        """Process a single Kafka message and extract relationships"""
        try:
            # Validate required fields
            user_id = payload.get("user_email") or "Guest"
            user_query = payload.get("user_query") or ""
            session_id = payload.get('session_id')
            
            print(f"[KGConsumer] Processing: user_id={user_id}, session_id={session_id}")
            
            if not user_query:
                print("[KGConsumer] ✗ Missing user_query in payload. Skipping.")
                return
            
            user_profile = payload.get("user_profile") or {"allergies": [], "conditions": [], "goals": []}
            product_json = payload.get("product_json") or {}

            # Format the prompt
            print(f"[KGConsumer] Formatting LLM extraction prompt...")
            prompt = KG_EXTRACT_PROMPT.format(
                user_id=user_id,
                user_query=user_query,
                user_profile=json.dumps(user_profile),
                product_json=json.dumps(product_json)
            )

            # Generate extraction using Gemini
            print(f"[KGConsumer] Calling Gemini API for relationship extraction...")
            response = self.client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )

            result_text = response.text.replace("```json", "").replace("```", "").strip()
            print(f"[KGConsumer] ✓ Received Gemini response")
            
            result_dict = json.loads(result_text)
            relationships = result_dict.get("relationships", [])
            print(f"[KGConsumer] ✓ Parsed {len(relationships)} relationships from LLM")

            # Load into Graph
            rel_count = 0
            for rel in relationships:
                source_id = rel.get("source_id")
                source_type = rel.get("source_type")
                target_id = rel.get("target_id")
                target_type = rel.get("target_type")
                rel_type = rel.get("relationship_type")

                if not all([source_id, source_type, target_id, target_type, rel_type]):
                    print(f"[KGConsumer] ⚠ Skipping malformed relationship: {rel}")
                    continue

                rel_count += 1
                print(f"[KGConsumer] Adding relationship: {source_id} ({source_type}) -[{rel_type}]-> {target_id} ({target_type})")
                self.graph_manager.add_relationship(
                    source_id=source_id,
                    source_type=source_type,
                    target_id=target_id,
                    target_type=target_type,
                    rel_type=rel_type
                )
            
            print(f"[KGConsumer] ✓ Successfully added {rel_count} relationships to knowledge graph\n")

        except json.JSONDecodeError as je:
            print(f"[KGConsumer] ✗ JSON parsing error: {je}")
            print(f"[KGConsumer] Response text: {response.text if 'response' in locals() else 'N/A'}")
            traceback.print_exc()
        except Exception as e:
            print(f"[KGConsumer] ✗ Error processing message: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    consumer = KGBuilderConsumer()
    consumer.run_forever()
