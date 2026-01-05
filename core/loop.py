import json
from core.llm import llm
from core.model import AgentState, UserProfile
from core.search import web_search
from core.prompts import TRIAGE_SYSTEM_PROMPT, RESPONSE_SYSTEM_PROMPT
from cv_layer.cv_extract import analyze_product

class Agent:
    def __init__(self):
        self.llm = llm(model_name="gemini-flash-lite-latest")

    def _parse_json(self, text: str):
        # Clean up markdown code blocks if present
        clean_text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)

    def step(self, state: AgentState) -> AgentState:
        current_input = state.user_query or state.image_data or ""

        # Step-0: Image Processing
        if state.image_data is None and getattr(state, "image_path", None):
            try:
                # analyze_product returns a dict
                parsed_dict = analyze_product(state.image_path)

                # Save raw JSON and OCR text
                state.product_json = parsed_dict
                state.image_data = json.dumps(parsed_dict, indent=2)

            except Exception as e:
                state.image_data = f"OCR/CV error: {e}"

        # Decide current input for agent reasoning
        if state.product_json:
            # Handle Pydantic model serialization if necessary, or dict
            if hasattr(state.product_json, 'dict'):
                current_input = json.dumps(state.product_json.dict(), indent=2)
            else:
                current_input = json.dumps(state.product_json, indent=2)
        else:
            current_input = state.user_query or state.image_data or ""


        # Step 1: Infer (Triage)
        try:
            formatted_infer = TRIAGE_SYSTEM_PROMPT.format(
                user_profile=state.user_profile,
                user_input=current_input
            )
            plan_raw = self.llm.ask(formatted_infer)
            plan_dict = self._parse_json(plan_raw)
            
            state.plan = plan_dict.get("reasoning", "")
            state.search_needed = plan_dict.get("needs_search", False)
            state.search_queries = plan_dict.get("search_queries", [])

            # Update profile from extraction
            extracted = plan_dict.get("extracted_entities", {})
            if extracted:
                state.user_profile.allergies.extend(extracted.get("allergies", []))
                state.user_profile.conditions.extend(extracted.get("conditions", []))
                state.user_profile.goals.extend(extracted.get("goals", []))

            # Deduplicate
            state.user_profile.conditions = list(set(state.user_profile.conditions))
            state.user_profile.allergies = list(set(state.user_profile.allergies))
            state.user_profile.goals = list(set(state.user_profile.goals))
            
        except Exception as e:
            print(f"Inference Error: {e}")
            state.plan = f"Infer error: {e}"
            state.search_needed = True
            state.search_queries = [current_input]


        # Step 2: Search
        if state.search_needed:
            results = []
            for query in state.search_queries:
                data = web_search(query)
                results.append(data)
            state.search_results = "\n\n".join(results)

        # Step 3: Synthesis (The Fix is Here)
        try:
            # 1. Serialize Product Data safely for the prompt
            product_data_str = "No product data detected."
            if state.product_json:
                if hasattr(state.product_json, 'dict'):
                    product_data_str = json.dumps(state.product_json.dict(), indent=2)
                else:
                    product_data_str = json.dumps(state.product_json, indent=2)

            # 2. Pass ALL required keys to .format()
            formatted_response = RESPONSE_SYSTEM_PROMPT.format(
                user_profile=state.user_profile,
                user_input=current_input,
                product_json=product_data_str,  # <--- THIS WAS MISSING
                search_context=state.search_results or "No external data."
            )
            
            response_raw = self.llm.ask(formatted_response)
            response_dict = self._parse_json(response_raw)
            
            state.final_verdict = response_dict.get("verdict")
            state.reasoning = response_dict.get("reasoning")
            state.next_suggestion = response_dict.get("suggested_next_steps", [])
            state.conversation_summary = response_dict.get("conversation_summary", "")

        except Exception as e:
            print(f"Synthesis Error details: {e}")
            state.final_verdict = "INFO"
            state.reasoning = f"Synthesis error: {e}"
            state.next_suggestion = []

        return state

if __name__ == "__main__":
    # Test logic...
    pass