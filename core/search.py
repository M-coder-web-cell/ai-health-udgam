from exa_py import Exa
from dotenv import load_dotenv
import os

load_dotenv()

exa = Exa(os.getenv('EXA_API_KEY'))

result = exa.stream_answer(
  "What are the health impacts of azelaic acid with correspondence to acne?",
  text=True,
)

for chunk in result:
    print(chunk, end="", flush=True)