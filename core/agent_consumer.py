import json
import time
import traceback

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from core.model import AgentState
from core.loop import Agent
from core.database import SessionLocal, ChatMessage, ChatSession


class AgentProcessorConsumer:

    def __init__(
        self,
        bootstrap_servers=["localhost:9092"],
        topic="user-queries"
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.agent = Agent()
        self.consumer = None

        print("\n===== INITIALIZING KAFKA CONSUMER =====")
        print(f"Topic: {self.topic}")
        print(f"Bootstrap Servers: {self.bootstrap_servers}")

        self._init_consumer()

    def _init_consumer(self):
        retry_count = 0
        max_retries = 10

        while retry_count < max_retries:
            try:
                print(
                    f"Connecting to Kafka "
                    f"({retry_count + 1}/{max_retries})..."
                )

                self.consumer = KafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id="agent-processor-group",
                    auto_offset_reset="earliest",
                    enable_auto_commit=True,
                    session_timeout_ms=30000,
                    request_timeout_ms=60000,
                    value_deserializer=lambda m: json.loads(
                        m.decode("utf-8")
                    )
                )

                print("✓ Kafka connected successfully")
                print(f"✓ Listening to topic: {self.topic}\n")

                return

            except KafkaError as e:
                retry_count += 1

                wait_time = min(5 * retry_count, 30)

                print(f"Kafka Error: {e}")
                print(f"Retrying in {wait_time}s...\n")

                time.sleep(wait_time)

            except Exception as e:
                retry_count += 1

                print(f"Unexpected Error: {e}")
                traceback.print_exc()

                time.sleep(5)

        raise RuntimeError(
            "Failed to connect to Kafka after retries"
        )

    def run_forever(self):
        print("\n===================================")
        print("   KAFKA STREAM CONSUMER STARTED")
        print("===================================\n")

        try:
            # TRUE STREAMING MODE
            # waits automatically for new messages
            for message in self.consumer:

                payload = message.value

                print("\n========== NEW MESSAGE ==========")
                print(f"Topic      : {message.topic}")
                print(f"Partition  : {message.partition}")
                print(f"Offset     : {message.offset}")

                print("\nPayload:")
                print(json.dumps(payload, indent=2))

                try:
                    self._process_message(payload)

                    print("\n✓ Message processed successfully")
                    print("================================\n")

                except Exception as e:
                    print(f"Processing Error: {e}")
                    traceback.print_exc()

        except KeyboardInterrupt:
            print("\nShutting down consumer...")

        finally:
            self._cleanup()

    def _process_message(self, payload):
        db = SessionLocal()

        try:
            session_id = payload.get("session_id")
            message_id = payload.get("message_id")
            state_data = payload.get("state")
            user_email = payload.get("user_email") or "Guest"

            print(
                f"\nProcessing:"
                f" session_id={session_id},"
                f" message_id={message_id}"
            )

            if not session_id:
                print("✗ Missing session_id")
                return

            if not state_data:
                print("✗ Missing state data")
                return

            # Reconstruct state object
            state = AgentState(**state_data)

            print("Running AI agent...\n")

            updated_state = self.agent.step(
                state,
                user_id=user_email
            )

            print("✓ AI execution completed")
            print(f"Verdict: {updated_state.final_verdict}")

            # Update existing message
            if message_id:

                msg = db.query(ChatMessage).filter(
                    ChatMessage.id == message_id
                ).first()

                if msg:
                    msg.ai_msg = updated_state.reasoning
                    msg.verdict = updated_state.final_verdict

                    db.commit()

                    print("✓ Existing DB message updated")

                else:
                    self._create_new_message(
                        db,
                        session_id,
                        updated_state
                    )

            # Create new message
            else:
                self._create_new_message(
                    db,
                    session_id,
                    updated_state
                )

        except Exception as e:
            print(f"✗ Error processing message: {e}")

            traceback.print_exc()

            db.rollback()

        finally:
            db.close()

    def _create_new_message(
        self,
        db,
        session_id,
        state
    ):
        if not session_id:
            new_session = ChatSession(
                title=f"Scan: {state.user_query[:20]}..."
            )

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

        print(f"✓ New DB message created for session {session_id}")

    def _cleanup(self):
        print("\nCleaning up consumer...")

        if self.consumer:
            try:
                self.consumer.close()

                print("✓ Consumer closed successfully")

            except Exception as e:
                print(f"Error closing consumer: {e}")


if __name__ == "__main__":
    consumer = AgentProcessorConsumer()
    consumer.run_forever()