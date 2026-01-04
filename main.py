from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from core.model import AgentState
from core.loop import Agent
import uuid
import os
import uvicorn

app = FastAPI()

# --- 1. Fix CORS (Allow All Origins) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (localhost:3000, etc.)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

agent = Agent()
UPLOAD_DIR = "server_storage"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/process", response_model=AgentState)
async def process_agent(state: AgentState):
    """
    Main Brain Endpoint:
    Receives JSON State -> Runs Agent Logic -> Returns Updated State
    """
    try:
        updated_state = agent.step(state)
        return updated_state
    except Exception as e:
        print(f"Error in /process: {e}") # Log error to terminal for debugging
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_to_disk(file: UploadFile = File(...)):
    """
    Simple Image Upload Endpoint.
    1. Receives image file.
    2. Saves to 'server_storage/'.
    3. Returns the local file path.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(file_path, "wb") as buffer:
            while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                buffer.write(content)
        

        return {"filename": unique_filename, "path": file_path}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload: {e}")


if __name__ == "__main__":
    try:
        # Changed host to 127.0.0.1 for better Windows compatibility sometimes, 
        # but 0.0.0.0 is fine if you need external access.
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("\nStopping AI-Health-Udgam server gracefully...")
    except Exception as e:
        print(f"Unexpected error: {e}")