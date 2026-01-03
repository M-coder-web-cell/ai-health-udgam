import json
from llm import llm
from model import AgentState, UserProfile
from search import web_search
from prompts import TRIAGE_SYSTEM_PROMPT, RESPONSE_SYSTEM_PROMPT

class Agent:
    def __init__(self):
        self.llm = llm(model_name="gemini-flash-lite-latest")

    def _parse_json(self, text: str):
        clean_text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)

    def step(self, state: AgentState) -> AgentState:
        current_input = state.user_query or state.image_data or ""

        # Step 1: Infer
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
        except Exception as e:
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

        # Step 3: Synthesis
        try:
            formatted_response = RESPONSE_SYSTEM_PROMPT.format(
                user_profile=state.user_profile,
                user_input=current_input,
                search_context=state.search_results or "No external data."
            )
            response_raw = self.llm.ask(formatted_response)
            response_dict = self._parse_json(response_raw)
            
            state.final_verdict = response_dict.get("verdict")
            state.reasoning = response_dict.get("reasoning")
            state.next_suggestion = response_dict.get("suggested_next_steps", [])
        except Exception as e:
            state.final_verdict = "INFO"
            state.reasoning = f"Synthesis error: {e}"
            state.next_suggestion = []

        return state

if __name__ == "__main__":
    # 1. Initialize User Profile
    # Using your existing UserProfile structure
    my_profile = UserProfile(
        allergies=["Sulfur"],
        conditions=["Pregnancy"],
        goals=["Clear skin", "Safe skincare"]
    )

    # 2. Setup Initial Agent State
    # We populate the required 'plan' and 'next_suggestion' as empty for start
    initial_state = AgentState(
        user_profile=my_profile,
        user_query="Is azelaic acid safe to use during pregnancy for hormonal acne?",
        plan="", 
        next_suggestion=[]
    )

    # 3. Initialize Agent and Execute
    # Ensure your Agent class and llm class are in scope or imported
    bot = Agent()
    
    print("🚀 Starting Health Agent Loop...")
    final_state = bot.step(initial_state)

    # 4. Verification & Output
    print("\n" + "="*30)
    print("STEP 1: INFER (Planning)")
    print("="*30)
    print(f"Plan/Reasoning: {final_state.plan}")
    print(f"Search Needed: {final_state.search_needed}")
    print(f"Queries Generated: {final_state.search_queries}")

    if final_state.search_needed:
        print("\n" + "="*30)
        print("STEP 2: SEARCH (External Knowledge)")
        print("="*30)
        # Showing a snippet of the Exa results stored in state
        print(f"Results gathered ({len(final_state.search_results)} chars).")

    print("\n" + "="*30)
    print("STEP 3: SYNTHESIS (Final Verdict)")
    print("="*30)
    print(f"VERDICT: {final_state.final_verdict}")
    print(f"REASONING: {final_state.reasoning}")
    print(f"SUGGESTIONS: {final_state.next_suggestion}")