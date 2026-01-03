from pydantic import BaseModel
from typing import List, Optional

class UserProfile(BaseModel):
    allergies: List[str] = []
    conditions: List[str] = [] # e.g. "Diabetic", "Pregnant"
    goals: List[str] = []      # e.g. "Muscle gain"

class AgentState(BaseModel):
    user_profile: UserProfile
    image_data: Optional[str] = None # OCR text or Image Description
    user_query: Optional[str] = None
    
    # Internal Memory
    
    plan: str
    search_needed: bool = False
    search_queries: List[str] = []
    search_results: str = ""
    
    # The Final Output
    final_verdict: Optional[str] = None # SAFE / CAUTION / DANGER
    reasoning: Optional[str] = None

    next_suggestion : List[str]