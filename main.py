import os
import json
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from core.model import AgentState
from core.loop import Agent
import uvicorn

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
SECRET_KEY = os.getenv("SECRET_KEY")

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth = OAuth()
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

agent = Agent()
UPLOAD_DIR = "server_storage"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        request.session['user'] = dict(user_info)
        
        return RedirectResponse(url='http://localhost:5173') 
    except Exception as e:
        print(f"Auth Error: {e}")
        return RedirectResponse(url='http://localhost:5173?error=auth_failed')


@app.get("/auth/me")
async def get_current_user(request: Request):
    user = request.session.get('user')
    if user:
        return user
    return JSONResponse(status_code=401, content={"detail": "Not authenticated"})


@app.get("/logout")
async def logout(request: Request):
    request.session.pop('user', None)
    return {"message": "Logged out"}


@app.post("/process")
async def process_agent(
    request: Request,
    file: UploadFile = File(None), 
    state_json: str = Form(...)
):
    user = request.session.get('user')
    user_email = user.get('email') if user else "Guest"
    print(f"Processing request for: {user_email}")

    try:
        state_dict = json.loads(state_json)
        state = AgentState(**state_dict)
        
        if file:
            extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{extension}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            with open(file_path, "wb") as buffer:
                while content := await file.read(1024 * 1024):
                    buffer.write(content)
            state.image_data = file_path
            
        updated_state = agent.step(state)
        return updated_state

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
