from sqlalchemy import create_engine, Column, String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
import datetime


DATABASE_URL =""
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    #google sub is the sirect mapping
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    picture = Column(String)


    # SERIALIZATION LOGIC:
    # SQL databases (like SQLite) cannot store Python Lists (e.g., ['dust', 'pollen']) directly.
    # Solution: We store them as Text strings containing JSON.
    #   - Save: json.dumps(['dust']) -> "['dust']"
    #   - Load: json.loads("['dust']") -> ['dust']
    allergies = Column(Text, default = "[]")
    conditions = Column(Text, default = "[]")


#the message storing will contain two parts 
#1.session-container - stores the session chat name and messages linked to it
#message table which will have the session id as a foreign key to link it to the session
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))

    title = Column(String, default="New Scan") # e.g., "Scan: Granola Bar"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    
    # The actual interaction pair
    human_msg = Column(Text)
    ai_msg = Column(Text)
    verdict = Column(String) 
    
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    session = relationship("ChatSession", back_populates="messages")

def init_db():
    """
    The Architect:
    Scans all classes inheriting from 'Base' (like User) and creates 
    the actual SQL tables if they don't exist yet.
    Must be called once on app startup.
    """
    Base.metadata.create_all(bind=engine)


#yeild and depends work together, depends is an automated fastapi tool that executes Depends(get_db()) and executes until yeild
#then handovers the session to the route using argument
#Once your route sends a response (or crashes), Depends goes back to get_db and runs the code after the yield (the finally block).
def get_db():
    #it opens a dedicated database session for incoming requests and yeilds the session object to the routehandler
    #finally block ensures that the session is closed after the request has been served so that no open or
    # hanging connections can crash the server
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

