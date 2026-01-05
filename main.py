from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from core.model import AgentState
from core.loop import Agent
import uuid
import os
import json
import uvicorn

app = FastAPI()

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = Agent()
UPLOAD_DIR = "server_storage"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/process")
async def process_agent(
    # 1. Accept optional file upload
    file: UploadFile = File(None), 
    # 2. Accept the JSON state as a raw string form field
    state_json: str = Form(...)    
):
    """
    Unified Endpoint:
    1. Parses 'state_json' string back into a Pydantic AgentState object.
    2. If a file is provided, saves it and updates state.image_data with the path.
    3. Runs the Agent Logic.
    4. Returns the final JSON state.
    """
    try:
        # A. Parse the JSON string into the Pydantic Model
        try:
            state_dict = json.loads(state_json)
            state = AgentState(**state_dict)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON state: {e}")

        # B. Handle File Upload (Middleware Logic)
        if file:
            if not file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
            
            # Save file
            extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{extension}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            with open(file_path, "wb") as buffer:
                while content := await file.read(1024 * 1024):
                    buffer.write(content)
            
            # C. Update State: Inject the path so the Agent can read it
            # This ensures core/loop.py can access the file at this path
            state.image_path = file_path
            
        # D. Run the Agent "Brain"
        updated_state = agent.step(state)
        
        return updated_state

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

