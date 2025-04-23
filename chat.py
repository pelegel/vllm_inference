import requests
import json
import sys 
from typing import Dict


# ====== MEMORY STORE FOR CHAT HISTORIES ======
conversations: Dict[str, list] = {}

DEFAULT_SYSTEM_PROMPT = {
    "role": "system",
    "content": [{"type": "text", "text": "תענה בבקשה על שאלות המשתמש בשפה העברית."}]
}


# Initialize a new session in conversation history if doesn't exists
def get_or_create_session(session_id: str) -> str:
    if session_id not in conversations:
        conversations[session_id] = {"messages": [DEFAULT_SYSTEM_PROMPT]}
    return session_id



def stream_chat(prompt, session_id):
    url = "http://localhost:8090/stream"
    headers = {"Content-Type": "application/json"}

    session_id = get_or_create_session(session_id)

    # Save user's response in conversation history  
    conversations[session_id]["messages"].append({"role": "user", "content": [{"type": "text", "text": prompt}]})

    response = ""
    with requests.post(url, headers=headers, json=conversations[session_id], stream=True) as r:
            for line in r.iter_lines():
                if line and line.startswith(b"data:"):
                    try:
                        chunk = json.loads(line.lstrip(b"data: ").decode("utf-8"))
                        print(chunk['choices'][0]['delta'].get('content', ''), end='', flush=True)
                        response += chunk['choices'][0]['delta'].get('content', '')
                    except json.JSONDecodeError:
                        continue

    # Save assistant's response in conversation history    
    conversations[session_id]["messages"].append({"role": "assistant", "content": [{"type": "text", "text": response}]})

    print("\n", end='', flush=True)
    print(conversations, end='', flush=True)
    print("\n======================================", end='', flush=True)



if __name__ == "__main__":

    prompt = input("\nEnter your prompt (type 'bye' to exit): ")
    session_id = 1
    # session_id = sys.argv[1]

    while prompt != "bye":
        stream_chat(prompt, session_id)
        print()
        prompt = input("\nEnter your prompt (type 'bye' to exit): ")
        # print(prompt)
