from sqlalchemy import create_engine, Column, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base


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


def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()