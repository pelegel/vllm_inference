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
import matplotlib.pyplot as plt


torch.cuda.empty_cache()

num_users = 25
max_concurrent = 25

tokens = []
times = []

total_context_length = 0

# Load tokenizer
model_id = "gaunernst/gemma-3-12b-it-qat-autoawq"
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)

url = "http://localhost:8090/stream"
headers = {"Content-Type": "application/json"}

model_id_clean = model_id.replace("/", "-")
file_name = f"{model_id_clean}_{num_users}_users"


# ====== MEMORY STORE FOR CHAT HISTORIES ======
conversations: Dict[str, list] = {}

DEFAULT_SYSTEM_PROMPT = {
    "role": "system",
    "content": [{"type": "text", "text": "תענה בבקשה על שאלות המשתמש בשפה העברית."}]
}


def get_or_create_session(session_id: str) -> str:
    if session_id not in conversations:
        conversations[session_id] = {"messages": [DEFAULT_SYSTEM_PROMPT]}
    return session_id


def count_tokens(text):
    return len(tokenizer.encode(str(text)))


def save_results(i, promot_count, prompt, response, response_tokens, duration, queue_time, conversation_context_length, total_context_length):
    
    with open(f"/workspace/user_{i}.txt", "a") as f:             # Generated response and statistics
        f.write(f"========== Prompt {promot_count} ==========\n")
        f.write(f"Prompt: {prompt}\n\n")
        f.write(f"Response:\n{response}\n\n")
        f.write(f"[Duration: {duration:.2f}s | T/s: {response_tokens / duration:.2f} | Queue: {queue_time:.2f}s | Context: {conversation_context_length} tokens]\n\n\n")

    with open(f"/workspace/generation_speeds.txt", "a") as f:         # Response generation speed
        f.write(f"{str(response_tokens/duration)}\n")
        
    with open(f"/workspace/durations.txt", "a") as f:                 # Response generation duration
        f.write(f"{duration}\n")

    with open(f"/workspace/queue_times.txt", "a") as f:               # Request's time in queue
        f.write(f"{queue_time}\n")


        
    with open(f"/workspace/total_context_length.txt", "a") as f:      # Context length after current response
        f.write(f"{total_context_length}\n")
        


def plot_requests_status(running, waiting):
    x = [i for i in range(len(waiting))]

    plt.plot(x, running, label="Running", color="blue")
    plt.plot(x, waiting, label="Waiting", color="orange")

    # plt.xlabel("Index")
    # plt.ylabel("Value")
    plt.title("Runing and Waiting Requests")
    plt.legend()
    plt.grid(True)
    plt.savefig("/workspace/Runing_and_Waiting_Requests.png", dpi=300, bbox_inches="tight")


def plot_queue_times(queue_times):
    x = [i for i in range(len(queue_times))]
    plt.bar(x, queue_times)
    plt.xlabel("Request")
    plt.ylabel("Queue time")
    plt.title("Requests Queue Time")
    plt.grid(True)
    plt.savefig("/workspace/Requests_Queue_Time.png", dpi=300, bbox_inches="tight")


def plot_generation_speed(generation_speeds, total_context_length):
    x = total_context_length
    plt.plot(x, generation_speeds, label="Waiting", color="orange")
    plt.xlabel("Context Length")
    plt.ylabel("T/s")
    plt.title("Generation Speed vs Context Length")
    plt.grid(True)
    plt.savefig("/workspace/Generation_Speed_vs_Context_Length.png", dpi=300, bbox_inches="tight")




def stream_chat(prompts, i):
    
    global url, headers, total_context_length

    session_id = get_or_create_session(i)
    promot_count = 0

    for prompt in prompts[str(session_id+1)]:
        promot_count += 1
        
        # Save user's prompt in conversation history  
        formatted_prompt = {"role": "user", "content": [{"type": "text", "text": prompt}]}
        conversations[session_id]["messages"].append(formatted_prompt)
        prompt_tokens = count_tokens(formatted_prompt)
        total_context_length += prompt_tokens
        
        response = ""
        send_time = time.time()
        
        print(f"\n========== User {i}, Prompt {promot_count} ==========\n", end='', flush=True)
        
        with requests.post(url, headers=headers, json=conversations[session_id], stream=True) as r:
            start_time = time.time()
            for line in r.iter_lines():
                if line and line.startswith(b"data:"):
                    try:
                        chunk = json.loads(line.lstrip(b"data: ").decode("utf-8"))
                        toks = chunk['choices'][0]['delta'].get('content', '')
                        response += toks
                        total_context_length += count_tokens(toks)
                        print(f"User {i} Prompt {promot_count}: {toks} \t\t\t total context length: {total_context_length}\n", "\n", end='', flush=True)

                    except json.JSONDecodeError:
                        continue

        # Duration of current response                    
        end_time = time.time()
        duration = end_time - start_time
        queue_time = start_time - send_time
        
        # Save assistant's response in conversation history    
        conversations[session_id]["messages"].append({"role": "assistant", "content": [{"type": "text", "text": response}]})

        # Tokens count for current response
        response_tokens = count_tokens({"role": "assistant", "content": [{"type": "text", "text": response}]})
        conversation_context_length = count_tokens(conversations[session_id])
        response_t_s = str(response_tokens/duration)
        total_context_length += count_tokens({"role": "assistant", "content": [{"type": "text", "text": ""}]})

        save_results(i, promot_count, prompt, response, response_tokens, duration, queue_time, conversation_context_length, total_context_length)
        time.sleep(10)

        

if __name__ == "__main__":

    with open("/prompts.json", 'r', encoding='utf-8') as file:
        prompts = json.load(file)

    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = []
        for i in range(num_users):
            futures.append(executor.submit(stream_chat, prompts, i))
            time.sleep(3)  # wait 3 second before starting the next thread
    
        for future in as_completed(futures):
            future.result()

    print("All threads done.")


    with open("/workspace/running.txt", "r") as f:
        running = [float(line.strip()) for line in f if line.strip()]

    with open("/workspace/waiting.txt", "r") as f:
        waiting = [float(line.strip()) for line in f if line.strip()]

    with open("/workspace/generation_speeds.txt", "r") as f:
        generation_speeds = [float(line.strip()) for line in f if line.strip()]

    with open("/workspace/durations.txt", "r") as f:
        durations = [float(line.strip()) for line in f if line.strip()]

    with open("/workspace/queue_times.txt", "r") as f:
        queue_times = [float(line.strip()) for line in f if line.strip()]

    with open("/workspace/total_context_length.txt", "r") as f:
        total_context_length = [float(line.strip()) for line in f if line.strip()]

    plot_requests_status(running, waiting)
    plot_queue_times(queue_times)
    plot_generation_speed(generation_speeds, total_context_length)


