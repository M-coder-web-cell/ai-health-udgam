# main.py
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from db import init_db, save_state, load_state
from cv_layer.cv_extract import analyze_product
from core.loop import Agent
from scripts.interactive_agent import interactive_agent
from model import UserProfile, AgentState
import json
import uuid
import time

app = FastAPI()

@app.on_event("startup")
def startup():
    init_db()

@app.get("/analyze")
def analyze(
    user_query: str = Query(None),
    image_path: str = Query(None)
):
    session_id = str(uuid.uuid4())  # unique session per user

    def event_stream():
        # Initialize the agent
        agent = Agent()
        
        # Initialize user profile and state
        user_profile = UserProfile(
            allergies=[],
            conditions=[],
            goals=[]
        )
        state = AgentState(user_profile=user_profile, user_query=user_query)

        yield {"stage": "init", "message": "Agent initialized."}

        # Step 1: Process image if provided
        if image_path:
            yield {"stage": "ocr", "message": "Processing image..."}
            try:
                product_json = analyze_product(image_path)
                state.image_data = product_json  # store OCR + parsed JSON
                yield {
                    "stage": "ocr_done",
                    "message": "OCR + LLM parsing complete",
                    "data": product_json
                }
            except Exception as e:
                yield {"stage": "ocr_error", "message": str(e)}

        # Step 2: Run interactive agent for initial reasoning
        yield {"stage": "reasoning", "message": "Running interactive agent..."}
        try:
            for step in interactive_agent(
                session_id=session_id,
                user_query=user_query,
                image_path=image_path
            ):
                # Each step from interactive_agent is a dict
                save_state(session_id, json.dumps(step, indent=2))
                yield {
                    "stage": step.get("stage", "interactive"),
                    "message": step.get("message", ""),
                    "data": step.get("data", {}),
                    "final_verdict": step.get("final_verdict"),
                    "reasoning": step.get("reasoning"),
                    "suggestions": step.get("next_suggestion", [])
                }
        except Exception as e:
            yield {"stage": "interactive_error", "message": str(e)}

        # Step 3: Keep agent loop alive for new user inputs
        while True:
            saved_state_json = load_state(session_id)
            if saved_state_json:
                state_dict = json.loads(saved_state_json)
                state = AgentState(**state_dict)

            if state.user_query:
                state = agent.step(state)
                save_state(session_id, json.dumps(state.dict(), indent=2))
                yield {
                    "stage": "update",
                    "message": "Processed new user input",
                    "final_verdict": state.final_verdict,
                    "reasoning": state.reasoning,
                    "suggestions": state.next_suggestion
                }
            time.sleep(1)  # prevent CPU overuse

    return StreamingResponse(event_stream(), media_type="text/event-stream")
