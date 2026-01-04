# core/model.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class ProductData(BaseModel):
    """
    Structured representation of a product extracted from CV / OCR layer.
    """
    product_name: Optional[str] = None
    company_name: Optional[str] = None
    IngredientList: List[str] = Field(default_factory=list)
    NutritionFacts: Dict[str, str] = Field(default_factory=dict)
    MarketingClaims: List[str] = Field(default_factory=list)

class UserProfile(BaseModel):
    allergies: List[str] = []
    conditions: List[str] = []
    goals: List[str] = []

class AgentState(BaseModel):
    user_query: str
    user_profile: UserProfile
    image_data: Optional[str] = None
    image_path: Optional[str] = None
    product_json: ProductData = None
    
    # FIX: Add '= None' or '= []' to make these optional in the input
    plan: Optional[str] = None 
    search_needed: bool = False
    search_queries: List[str] = []
    search_results: Optional[str] = None
    
    final_verdict: Optional[str] = None
    reasoning: Optional[str] = None
    next_suggestion: List[str] = [] # Defaults to empty list
    conversation_summary: Optional[str] = None