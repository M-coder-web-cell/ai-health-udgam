from fastapi import FastAPI, HTTPException
from core.model import AgentState
from core.loop import Agent
import uvicorn

app = FastAPI()
agent = Agent()

@app.post("/process", response_model=AgentState)
async def process_agent(state: AgentState):
    """
    Endpoint receives JSON -> Converts to AgentState Pydantic Object
    -> Runs Agent Logic -> Returns Object -> Converts back to JSON
    """
    try:
        updated_state = agent.step(state)
        return updated_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    try:
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("\nStopping AI-Health-Udgam server gracefully...")
    except Exception as e:
        print(f"Unexpected error: {e}")