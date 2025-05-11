
import subprocess
import requests
import time
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from transformers import AutoTokenizer
from typing import Dict
import torch


torch.cuda.empty_cache()

num_users = 25
max_concurrent = 25

tokens = []
times = []

total_context_length = 0

# Load tokenizer
model_id = "gaunernst/gemma-3-12b-it-qat-autoawq"
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)


model_id_clean = model_id.replace("/", "-")
file_name = f"{model_id_clean}_{num_users}_users"

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
    

def count_tokens(text):
    return len(tokenizer.encode(str(text)))
               

def stream_chat(prompts, i, send_time):
    url = "http://localhost:8090/stream"
    headers = {"Content-Type": "application/json"}
    global total_context_length

    session_id = get_or_create_session(i)
    promot_count = 0

    for prompt in prompts[str(session_id)]:
        promot_count += 1
        
        # Save user's prompt in conversation history  
        conversations[session_id]["messages"].append({"role": "user", "content": [{"type": "text", "text": prompt}]})
        prompt_tokens = count_tokens({"role": "user", "content": [{"type": "text", "text": prompt}]})
        total_context_length += prompt_tokens
        
        response = ""
        
        print(f"\n######################### User {i}, Prompt {promot_count}:#########################\n", end='', flush=True)


        
        with requests.post(url, headers=headers, json=conversations[session_id], stream=True) as r:
            # Start counting time for the current prompt
            start_time = time.time()
            for line in r.iter_lines():
                if line and line.startswith(b"data:"):
                    try:
                        chunk = json.loads(line.lstrip(b"data: ").decode("utf-8"))
                        total_context_length += count_tokens(chunk['choices'][0]['delta'].get('content', ''))
                        print(f"User {i} Prompt {promot_count}: {chunk['choices'][0]['delta'].get('content', '')} \t\t\t total context length: {total_context_length}\n", "\n", end='', flush=True)
                        response += chunk['choices'][0]['delta'].get('content', '')
    
                    except json.JSONDecodeError:
                        continue
    
        # Save assistant's response in conversation history    
        conversations[session_id]["messages"].append({"role": "assistant", "content": [{"type": "text", "text": response}]})
    
        # Duration of current response                    
        end_time = time.time()
        duration = end_time - start_time
        times.append(duration)

        # Tokens count for current response
        response_tokens = count_tokens({"role": "assistant", "content": [{"type": "text", "text": response}]})
        total_context_length += count_tokens({"role": "assistant", "content": [{"type": "text", "text": ""}]})

        
        # Conversation history context length
        conversation_context_length = count_tokens(conversations[session_id])

        # Write response to file
        with open(f"/workspace/user_{i}.txt", "a") as f:
            f.write(f"---------- Prompt {promot_count}: {prompt} ---------- \n\n")
            f.write(f"{response}\n\n\n duration: {duration}, T/s: {str(response_tokens/duration)} queue time: {send_time-start_time} , conversation context length: {conversation_context_length}\n\n\n\n")

        # Write duration and speed data to file
        with open(f"/workspace/{file_name}.txt", "a") as f:
            f.write(f"\n**User {i} Prompt {promot_count}:** duration: {duration}, T/s: {str(response_tokens/duration)} conversation context length: {conversation_context_length}, total context length: {total_context_length} \n")

        # Simulate a short break
        time.sleep(10)




if __name__ == "__main__":
    
    with open(f"/workspace/{file_name}.txt", "a") as f:
        f.write("#############################################################\n")
        f.write(f"### Model: {model_id}, Users: {num_users} ###\n")
        f.write("#############################################################\n")

    
    with open("/prompts.json", 'r', encoding='utf-8') as file:
        prompts = json.load(file)
        
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = []
        for i in range(num_users):
            send_time = time.time()
            futures.append(executor.submit(stream_chat, prompts, i, send_time))
            time.sleep(3)  # wait 3 second before starting the next thread
    
        for future in as_completed(futures):
            future.result()

    print("All threads done.")

    plot_durations(times, tokens)
