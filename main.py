import os
import json
import time
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import uvicorn
from utilities.base64Utils import saveToFile

# Imports from core
from core.model import AgentState
from core.database import init_db, SessionLocal, ChatSession, ChatMessage
from kafka_app.producer import send_message

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

UPLOAD_DIR = "server_storage"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.on_event("startup")
async def startup_event():
    init_db()
    print("[Server] Database initialized.")


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
    state : AgentState
):
    user = request.session.get('user')
    user_id = user.get('sub') if user else "Guest"
    user_email = user.get('email') if user else "Guest"
    print(f"[API /process] Received query request for: {user_email}")

    db = SessionLocal()
    try:
        # Check if we should reuse or create a ChatSession
        # We can extract a custom body JSON to see if session_id is provided, otherwise create a new session
        # Prefer the parsed Pydantic `state`; avoid re-reading the request body stream
        session_id = None
        try:
            session_id = getattr(state, "session_id", None)
        except Exception:
            session_id = None

        img_encodedstr = getattr(state, "image_encodedstr", None)
        if img_encodedstr:
            try:
                state.image_path = saveToFile(img_encodedstr)
            except Exception as e:
                print(f"Image save error: {e}")

        if not session_id:
            db_session = ChatSession(
                user_id=user_id,
                title=f"Scan: {state.user_query[:20] if state.user_query else 'New Product'}"
            )
            db.add(db_session)
            db.commit()
            db.refresh(db_session)
            session_id = db_session.id
        
        # Create placeholder chat message in DB
        db_msg = ChatMessage(
            session_id=session_id,
            human_msg=state.user_query,
            ai_msg=None,  # Placeholder (to be updated by Agent consumer)
            verdict=None
        )
        db.add(db_msg)
        db.commit()
        db.refresh(db_msg)
        message_id = db_msg.id

        # Package state and contexts for streaming Kafka queue
        kafka_payload = {
            "session_id": session_id,
            "message_id": message_id,
            "user_email": user_email,
            "state": state.dict(),
            "user_query": state.user_query,
            "user_profile": state.user_profile.dict(),
            "product_json": state.product_json if hasattr(state.product_json, 'dict') else state.product_json
        }

        # Produce payload to Kafka
        send_message("user-queries", kafka_payload)
        
        return JSONResponse(
            status_code=202,
            content={
                "status": "processing",
                "session_id": session_id,
                "message_id": message_id,
                "detail": "Safety evaluation is processing in the background."
            }
        )

    except Exception as e:
        print(f"Error starting async process: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/session/{session_id}/messages")
async def get_session_messages(session_id: int):
    """
    Polling endpoint allowing the client to retrieve the chat interaction log.
    If the consumer has completed processing, 'ai_msg' will be populated.
    """
    db = SessionLocal()
    try:
        messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.timestamp.asc()).all()
        result = []
        for msg in messages:
            result.append({
                "id": msg.id,
                "human_msg": msg.human_msg,
                "ai_msg": msg.ai_msg,
                "verdict": msg.verdict,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/stream/session/{session_id}")
async def stream_session_messages(session_id: int):
    """
    Server-Sent Events (SSE) endpoint that streams message updates in real-time.
    Client connects and receives events as the consumer updates the database.
    """
    async def event_generator():
        last_check = {}
        max_timeout = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_timeout:
            db = SessionLocal()
            try:
                messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.timestamp.asc()).all()
                
                for msg in messages:
                    msg_key = msg.id
                    msg_data = {
                        "id": msg.id,
                        "human_msg": msg.human_msg,
                        "ai_msg": msg.ai_msg,
                        "verdict": msg.verdict,
                        "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
                    }
                    
                    # Only send if data changed (avoids duplicate events)
                    if msg_key not in last_check or last_check[msg_key] != msg_data:
                        last_check[msg_key] = msg_data
                        yield f"data: {json.dumps(msg_data)}\n\n"
                        
                        # If message has been completed (ai_msg populated), allow stream to close
                        if msg.ai_msg and msg.verdict:
                            yield "event: done\ndata: {}\n\n"
                            return
                
            except Exception as e:
                print(f"[SSE] Error in event_generator: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            finally:
                db.close()
            
            # Poll DB every 1 second for updates
            await asyncio.sleep(1)
        
        # Timeout reached
        yield "event: timeout\ndata: {}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
