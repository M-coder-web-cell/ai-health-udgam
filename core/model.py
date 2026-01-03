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
    """
    User's health profile and preferences
    """
    allergies: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)  # e.g. "Diabetic", "Pregnant"
    goals: List[str] = Field(default_factory=list)       # e.g. "Muscle gain", "Clear skin"


class AgentState(BaseModel):
    """
    Represents the internal state of the agent at each step.
    """
    user_profile: UserProfile

    # CV Output
    product_json: Optional[ProductData] = None
    image_data: Optional[str] = None  # Raw OCR text or image description
    user_query: Optional[str] = None  # User's natural language query

    # Internal Memory
    plan: str = ""
    search_needed: bool = False
    search_queries: List[str] = Field(default_factory=list)
    search_results: str = ""

    # Final output
    final_verdict: Optional[str] = None  # SAFE / CAUTION / DANGER / UNKNOWN
    reasoning: Optional[str] = None
    next_suggestion: List[str] = Field(default_factory=list)
