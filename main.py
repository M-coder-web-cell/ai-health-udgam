from fastapi import FastAPI, UploadFile, File, HTTPException
from core.model import AgentState
from core.loop import Agent
import uuid
import os
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


UPLOAD_DIR = "server_storage"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_to_disk(state : AgentState, file: UploadFile = File(...)):

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        while content := await file.read(1024 * 1024): 
            buffer.write(content)

    state.image_path = file_path
    return {"filename": unique_filename, "path": file_path}

if __name__ == "__main__":
    try:
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("\nStopping AI-Health-Udgam server gracefully...")
    except Exception as e:
        print(f"Unexpected error: {e}")