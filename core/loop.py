import json
import base64
from core.llm import llm
from core.model import AgentState, UserProfile
from core.search import web_search
from core.prompts import REACT_SYSTEM_PROMPT # Replace prior prompts with a unified one
from cv_layer.cv_extract import analyze_product

class Agent:
    def __init__(self):
        # Using the requested model
        self.llm = llm(model_name="gemini-flash-lite-latest")

    def _parse_json(self, text: str):
        clean_text = text.replace("```json", "").replace("
```", "").strip()
        return json.loads(clean_text)

    def step(self, state: AgentState) -> AgentState:
        # Step-0: Image Processing (Stays synchronous before the loop)
        if state.image_data is None and getattr(state, "image_path", None):
            try:
                parsed_dict = analyze_product(state.image_path)
                state.product_json = parsed_dict
                state.image_data = json.dumps(parsed_dict, indent=2)
            except Exception as e:
                state.image_data = f"OCR/CV error: {e}"

        # Serialize product data for the context
        product_data_str = "No product data detected."
        if state.product_json:
            if hasattr(state.product_json, 'dict'):
                product_data_str = json.dumps(state.product_json.dict(), indent=2)
            else:
                product_data_str = json.dumps(state.product_json, indent=2)

        # Establish current input context
        current_input = state.user_query or state.image_data or ""

        # Initialize local execution state for the ReAct loop
        search_history = []
        max_iterations = 3 
        
        for iteration in range(max_iterations):
            try:
                # Format the prompt, feeding back any gathered search results dynamically
                formatted_prompt = REACT_SYSTEM_PROMPT.format(
                    user_profile=state.user_profile,
                    user_input=current_input,
                    product_json=product_data_str,
                    search_history="\n".join(search_history) if search_history else "No search history yet."
                )

                # Single LLM Call per iteration
                llm_response = self.llm.ask(formatted_prompt)
                
                # Check if the LLM wants to execute a tool (e.g., search) or finish
                # Expected format from LLM: 
                # <reasoning>Thinking process...</reasoning>
                # ```json {...} ```
                
                # Extract JSON payload outside the reasoning tag
                response_dict = self._parse_json(llm_response)
                
                # Update state profile information immediately if found in payload
                extracted = response_dict.get("extracted_entities", {})
                if extracted:
                    state.user_profile.allergies.extend(extracted.get("allergies", []))
                    state.user_profile.conditions.extend(extracted.get("conditions", []))
                    state.user_profile.goals.extend(extracted.get("goals", []))
                    
                    # Deduplicate profile arrays
                    state.user_profile.conditions = list(set(state.user_profile.conditions))
                    state.user_profile.allergies = list(set(state.user_profile.allergies))
                    state.user_profile.goals = list(set(state.user_profile.goals))

                # Check action path
                action = response_dict.get("action")
                
                if action == "search":
                    query = response_dict.get("search_query")
                    if query:
                        raw_result = web_search(query)
                        search_history.append(f"Query: '{query}' -> Result: {raw_result}")
                    continue  # Loop back to LLM with new data
                    
                elif action == "final_response" or iteration == max_iterations - 1:
                    # Capture final properties and terminate the loop
                    state.final_verdict = response_dict.get("verdict", "INFO")
                    state.reasoning = response_dict.get("reasoning", "")
                    state.next_suggestion = response_dict.get("suggested_next_steps", [])
                    state.conversation_summary = response_dict.get("conversation_summary", "")
                    state.search_results = "\n\n".join(search_history)
                    break

            except Exception as e:
                print(f"Error during ReAct loop iteration {iteration}: {e}")
                state.final_verdict = "INFO"
                state.reasoning = f"Loop execution error: {e}"
                state.next_suggestion = []
                break

        return state