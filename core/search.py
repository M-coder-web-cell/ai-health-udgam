from exa_py import Exa
from dotenv import load_dotenv
import os

load_dotenv()
exa = Exa(os.getenv('EXA_API_KEY'))

def web_search(query):
    result = exa.stream_answer(
        query,
        text=True,
    )
    
    full_response = []
    for chunk in result:
        # Collect chunks to return as a full string
        full_response.append(str(chunk))
        
    return "".join(full_response)

# Example call:
# content = web_search("What are the health impacts of azelaic acid?")
# print(content)