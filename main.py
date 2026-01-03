from core.llm import llm

llm = llm(model_name="gemini-flash-lite-latest")
print(llm.ask("Explain how AI works in a few words"))
