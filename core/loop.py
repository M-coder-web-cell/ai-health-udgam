import json
from core.llm import llm
from core.model import AgentState
from core.search import web_search
from core.prompts import REACT_SYSTEM_PROMPT 
from cv_layer.cv_extract import analyze_product
from knowledge_store.graph_manager import HealthGraphManager

class Agent:
    def __init__(self):
        # Using the requested model
        self.llm = llm(model_name="gemini-flash-lite-latest")
        self.graph_manager = HealthGraphManager()

    def _parse_json(self, text: str):
        clean_text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)

    def step(self, state: AgentState, user_id: str = "Guest") -> AgentState:
        # Step-0: Image Processing (Stays synchronous before the loop)
        if state.image_data is None and getattr(state, "image_path", None):
            try:
                parsed_dict, _ = analyze_product(state.image_path)
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

        current_input = state.user_query or state.image_data or ""

        search_history = []
        max_iterations = 4  # Bumped slightly to allow deep graph traversal + search
        
        for iteration in range(max_iterations):
            try:
                # Format the prompt, feeding back any gathered search/graph results dynamically
                formatted_prompt = REACT_SYSTEM_PROMPT.format(
                    user_profile=state.user_profile,
                    user_input=current_input,
                    product_json=product_data_str,
                    search_history="\n".join(search_history) if search_history else "No tool history yet."
                )

                # Single LLM Call per iteration
                llm_response = self.llm.ask(formatted_prompt)
                
                # Check if the LLM wants to execute a tool (e.g., search) or finish
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
                
                if action == "get_user_subgraph":
                    subgraph_data = self.graph_manager.get_user_subgraph(user_id)
                    search_history.append(
                        f"Iteration {iteration+1} - Tool: 'get_user_subgraph' -> Output:\n{json.dumps(subgraph_data, indent=2)}"
                    )
                    continue

                elif action == "graph_path_search":
                    # Check list of ingredients in response or fallback to product ingredients
                    ingredients = response_dict.get("ingredients")
                    if not ingredients and state.product_json:
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