# core/agent.py

import json
import re
from core.llm import llm
from core.model import AgentState
from core.search import web_search
from core.prompts import REACT_SYSTEM_PROMPT 
from cv_layer.cv_extract import analyze_product
from knowledge_store.graph_manager import HealthGraphManager

class Agent:
    def __init__(self):
        # Initializing Gemini Flash Lite
        self.llm = llm(model_name="gemini-flash-lite-latest")
        self.graph_manager = HealthGraphManager()

    def _parse_json(self, text: str) -> dict:
        """
        Robustly extracts and parses JSON out of mixed markdown text responses.
        Handles text that contains reasoning blocks, code enclosures, or leading spaces.
        """
        if not text or not text.strip():
            raise ValueError("The LLM engine provided an completely empty text payload.")

        # Strip out the reasoning section if present to isolate raw JSON block context
        clean_text = re.sub(r'<reasoning>.*?</reasoning>', '', text, flags=re.DOTALL).strip()

        # Strip markdown syntax wrappers if model injected them
        clean_text = clean_text.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            # Fallback: Look for structural JSON markers if extra junk string exists
            match = re.search(r'\{.*\}', clean_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Failed to isolate valid JSON configuration pattern. Raw trace: {text[:150]}")

    def step(self, state: AgentState, user_id: str = "Guest") -> AgentState:
        # Step-0: Image Processing (Stays synchronous before the loop)
        if state.image_data is None and getattr(state, "image_path", None):
            try:
                parsed_dict, _ = analyze_product(state.image_path)
                state.product_json = parsed_dict
                state.image_data = json.dumps(parsed_dict, indent=2)
                print("Product analysed successfully")
            except Exception as e:
                state.image_data = f"OCR/CV error: {e}"

        # Serialize product data for the context
        product_data_str = "No product data detected."
        if state.product_json:
            if hasattr(state.product_json, 'dict'):
                product_data_str = json.dumps(state.product_json.dict(), indent=2)
                print(f"[loop] productjson updated successfully")
            else:
                product_data_str = json.dumps(state.product_json, indent=2)
                

        current_input = state.user_query or state.image_data or ""
        search_history = []
        max_iterations = 4
        
        for iteration in range(max_iterations):
            try:
                # Format the prompt dynamically with cumulative tracking data
                formatted_prompt = REACT_SYSTEM_PROMPT.format(
                    user_profile=state.user_profile,
                    user_input=current_input,
                    product_json=product_data_str,
                    search_history="\n".join(search_history) if search_history else "No tool history yet."
                )

                # Query the LLM
                llm_response = self.llm.ask(formatted_prompt)
                
                # Robust extraction parsing block
                try:
                    response_dict = self._parse_json(llm_response)
                except ValueError as json_err:
                    print(f"[Iteration {iteration+1}] Validation Parsing Mistake: {json_err}")
                    # Feed the structural issue back to the LLM so it auto-corrects on retry
                    search_history.append(
                        f"Iteration {iteration+1} - System Validation Error: Your output structure could not be parsed as valid JSON. "
                        f"Ensure you don't output text outside of <reasoning> tags and a single clean JSON schema structure."
                    )
                    continue

                # Process safely extracted entities
                extracted = response_dict.get("extracted_entities", {})
                if extracted:
                    if isinstance(extracted.get("allergies"), list):
                        state.user_profile.allergies.extend(extracted.get("allergies", []))
                    if isinstance(extracted.get("conditions"), list):
                        state.user_profile.conditions.extend(extracted.get("conditions", []))
                    if isinstance(extracted.get("goals"), list):
                        state.user_profile.goals.extend(extracted.get("goals", []))
                    
                    # Deduplicate profile arrays safely
                    state.user_profile.conditions = list(set(state.user_profile.conditions))
                    state.user_profile.allergies = list(set(state.user_profile.allergies))
                    state.user_profile.goals = list(set(state.user_profile.goals))

                # Route action payload execution
                action = response_dict.get("action")
                print(f"[Iteration {iteration+1}] Running action payload: {action}")
                
                if action == "get_user_subgraph":
                    subgraph_data = self.graph_manager.get_user_subgraph(user_id)
                    search_history.append(
                        f"Iteration {iteration+1} - Tool: 'get_user_subgraph' -> Output:\n{json.dumps(subgraph_data, indent=2)}"
                    )
                    continue

                elif action == "graph_path_search":
                    ingredients = response_dict.get("ingredients")
                    if not ingredients and state.product_json:
                        # Fallback query lookup default values
                        ingredients = state.product_json.get("IngredientList", [])
                    
                    paths = self.graph_manager.find_clinical_paths(user_id, ingredients or [])
                    search_history.append(
                        f"Iteration {iteration+1} - Tool: 'graph_path_search' for ingredients {ingredients} -> Output:\n{json.dumps(paths, indent=2)}"
                    )
                    continue

                elif action == "graph_query":
                    node_name = response_dict.get("node_name", "")
                    neighbors = self.graph_manager.get_node_neighbors(node_name)
                    search_history.append(
                        f"Iteration {iteration+1} - Tool: 'graph_query' for '{node_name}' -> Output:\n{json.dumps(neighbors, indent=2)}"
                    )
                    continue

                elif action == "search":
                    query = response_dict.get("search_query")
                    if query:
                        raw_result = web_search(query)
                        search_history.append(
                            f"Iteration {iteration+1} - Tool: 'search' query: '{query}' -> Output:\n{raw_result}"
                        )
                    continue
                    
                elif action == "final_response" or iteration == max_iterations - 1:
                    state.final_verdict = response_dict.get("verdict", "INFO")
                    state.reasoning = response_dict.get("reasoning", "Deduction completed successfully.")
                    state.next_suggestion = response_dict.get("suggested_next_steps", [])
                    state.conversation_summary = response_dict.get("conversation_summary", "")
                    state.search_results = "\n\n".join(search_history)
                    break

            except Exception as e:
                print(f"Critical execution fault during loop execution step {iteration}: {e}")
                state.final_verdict = "INFO"
                state.reasoning = f"Loop execution unexpected runtime fault: {e}"
                state.next_suggestion = []
                break

        return state
