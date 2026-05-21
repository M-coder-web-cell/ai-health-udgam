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
    allergies: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    goals: List[str] = Field(default_factory=list)

class AgentState(BaseModel):
    user_query: str
    user_profile: UserProfile
    image_data: Optional[ProductData] = None
    image_path: Optional[str] = None
    image_encodedstr: Optional[str] = None
    product_json: Optional[ProductData] = None

    plan: Optional[str] = None 
    search_needed: bool = False
    search_queries: List[str] = Field(default_factory=list)
    search_results: Optional[str] = None
    
    final_verdict: Optional[str] = None
    reasoning: Optional[str] = None
    next_suggestion: List[str] = Field(default_factory=list)
    conversation_summary: Optional[str] = None