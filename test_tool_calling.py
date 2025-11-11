"""
Test if Ollama tool calling works with the current setup
"""
import sys
sys.path.insert(0, 'src')

from ollama import chat

def simple_math(a: int, b: int) -> dict:
    """Add two numbers together"""
    return {"result": a + b}

print("Testing Ollama tool calling...")
print("Model: qwen3:latest")
print("-" * 50)

try:
    response = chat(
        model='qwen3:latest',
        messages=[
            {'role': 'user', 'content': 'Use the simple_math tool to add 5 and 3'}
        ],
        tools=[simple_math],
        options={'temperature': 0}
    )
    
    print("\n✅ Response received")
    
    # Handle Pydantic Message object
    message = response['message']
    print(f"Message type: {type(message)}")
    print(f"Message attributes: {dir(message)}")
    
    if hasattr(message, 'tool_calls') and message.tool_calls:
        print("\n✅ Tool calls detected!")
        tool_calls = message.tool_calls
        print(f"Number of tool calls: {len(tool_calls)}")
        for tc in tool_calls:
            print(f"  - Function: {tc.function.name}")
            print(f"  - Arguments: {tc.function.arguments}")
    else:
        print("\n❌ NO TOOL CALLS - Model generated text instead:")
        print(f"Content: {getattr(message, 'content', 'No content')}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
