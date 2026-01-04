# scripts/interactive_agent.py
import json
from cv_layer.cv_extract import analyze_product
from model import UserProfile, AgentState
from agent.loop import Agent
from db import save_state
import uuid

def interactive_agent(session_id: str, user_query: str = None, image_path: str = None):
    """
    Yields step updates as dict for FastAPI SSE.
    Saves state to DB after each step.
    """
    agent = Agent()

    # Initialize user profile & state
    user_profile = UserProfile(
        allergies=[],
        conditions=[],
        goals=[]
    )
    state = AgentState(user_profile=user_profile, user_query=user_query)

    yield {"stage": "init", "message": "Agent initialized."}

    # Step 1: OCR / CV layer
    if image_path:
        yield {"stage": "ocr", "message": "Processing image..."}
        try:
            product_json = analyze_product(image_path)
            state.image_data = product_json
            yield {"stage": "ocr_done", "message": "OCR + LLM parsing done", "data": product_json}
        except Exception as e:
            yield {"stage": "ocr_error", "message": str(e)}

    # Step 2: Agent reasoning (first loop iteration)
    yield {"stage": "reasoning", "message": "Running agent reasoning..."}
    state = agent.step(state)
    save_state(session_id, json.dumps(state.dict(), indent=2))
    yield {
        "stage": "done",
        "message": "Agent reasoning complete",
        "final_verdict": state.final_verdict,
        "reasoning": state.reasoning,
        "suggestions": state.next_suggestion
    }

    # Step 3: Continue running indefinitely for this session
    # (can be called again on new user input)
    while True:
        if state.user_query:
            state = agent.step(state)
            save_state(session_id, json.dumps(state.dict(), indent=2))
            yield {
                "stage": "update",
                "message": "New user input processed",
                "final_verdict": state.final_verdict,
                "reasoning": state.reasoning,
                "suggestions": state.next_suggestion
            }
