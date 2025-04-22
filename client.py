import requests
import json
import sys 

def stream_chat(prompt):
    url = "http://localhost:8090/stream"
    headers = {"Content-Type": "application/json"}
    data = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ]
            }
        ]
    }

    with requests.post(url, headers=headers, json=data, stream=True) as r:
            for line in r.iter_lines():
                if line and line.startswith(b"data:"):
                    try:
                        chunk = json.loads(line.lstrip(b"data: ").decode("utf-8"))
                        print(chunk['choices'][0]['delta'].get('content', ''), end='', flush=True)
                    except json.JSONDecodeError:
                        continue


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client.py \"your prompt here\"")
    else:
        prompt = sys.argv[1]
        stream_chat(prompt)