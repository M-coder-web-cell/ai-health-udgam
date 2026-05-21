import json
import time
import os
from kafka import KafkaConsumer
from core.model import AgentState, ProductData, UserProfile
from core.loop import Agent
from core.database import SessionLocal, ChatMessage, ChatSession
from dotenv import load_dotenv

load_dotenv()

class AgentProcessorConsumer:
    def __init__(self, bootstrap_servers=['localhost:9092'], topic='user-queries'):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.agent = Agent()

    def run_once(self):
        print(f"[AgentConsumer] Connecting to Kafka at {self.bootstrap_servers}...")
        consumer = None
        while not consumer:
            try:
                consumer = KafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id='agent-processor-group',
                    auto_offset_reset='latest',
                    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
                )
                print(f"[AgentConsumer] Connected successfully to topic '{self.topic}'.")
            except Exception as e:
                print(f"[AgentConsumer] Connection failed: {e}. Retrying in 5s...")
                time.sleep(5)

        try:
            msg_pack = consumer.poll(timeout_ms=1000)
            for topic_partition, messages in msg_pack.items():
                for message in messages:
                    payload = message.value
                    print(f"[AgentConsumer] Received message to process: Session ID: {payload.get('session_id')}")
                    self._process_message(payload)
        finally:
            consumer.close()

    def run_forever(self):
        while True:
            try:
                self.run_once()
                time.sleep(1)
            except KeyboardInterrupt:
                print("[AgentConsumer] Stopping on KeyboardInterrupt.")
                break
            except Exception as e:
                print(f"[AgentConsumer] Error in consume loop: {e}")
                time.sleep(2)

    def _process_message(self, payload):
        db = SessionLocal()
        try:
            session_id = payload.get("session_id")
            message_id = payload.get("message_id")
            state_data = payload.get("state")
            user_email = payload.get("user_email") or "Guest"
            
            if not state_data:
                print("[AgentConsumer] Missing state data in payload. Skipping.")
                return

            # Reconstruct AgentState object
            state = AgentState(**state_data)
            
            # Run ReAct Loop Step (augmented with Graph Tools)
            # We also pass user_email in context so graph tools can retrieve user's node
            updated_state = self.agent.step(state, user_id=user_email)

            # Store result in database
            if message_id:
                msg = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
                if msg:
                    msg.ai_msg = updated_state.reasoning
                    msg.verdict = updated_state.final_verdict
                    db.commit()
                    print(f"[AgentConsumer] Successfully updated existing message {message_id} in DB.")
                else:
                    self._create_new_message(db, session_id, updated_state)
            else:
                self._create_new_message(db, session_id, updated_state)

        except Exception as e:
            print(f"[AgentConsumer] Error processing message: {e}")
            db.rollback()
        finally:
            db.close()

    def _create_new_message(self, db, session_id, state):
        # Fallback: create session if needed, then insert message
        if not session_id:
            # Create a placeholder session
            new_session = ChatSession(title=f"Scan: {state.user_query[:20]}...")
            db.add(new_session)
            db.flush()
            session_id = new_session.id
            
        new_msg = ChatMessage(
            session_id=session_id,
            human_msg=state.user_query,
            ai_msg=state.reasoning,
            verdict=state.final_verdict
        )
        db.add(new_msg)
        db.commit()
        print(f"[AgentConsumer] Created new message in DB for Session {session_id}.")

if __name__ == "__main__":
    consumer = AgentProcessorConsumer()
    consumer.run_forever()
