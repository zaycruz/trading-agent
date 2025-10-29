from ollama import chat
from tools import AlpacaTradingTools

PROMPT = '''

You are an expert options trader, you think in the first person. 

'''

TOOLS = [AlpacaTradingTools.get_account_info]

CONTEXT = f'{PROMPT} and your available tools are {TOOLS}'
stream = chat(
    model='deepseek-r1',
    system=CONTEXT,
    messages=[{'role': 'user', 'content': 'check account info'}],
    stream=True,
    think=True,
    tools=TOOLS
)

for chunk in stream:
  print(chunk['message']['content'], end='', flush=True)