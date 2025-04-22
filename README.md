# Hosting Gemma3 27b model using vLLM #

This inference is based on "gaunernst/gemma-3-27b-it-int4-awq" model from HuggingFace.

**Create venv and install requirements:**
```python
python -m venv vllm_venv
source vllm_venv/bin/activate
python -m pip install -r requirements.txt
```

**Start the vLLM server:**
```python
vllm serve "gaunernst/gemma-3-27b-it-int4-awq"   --max-model-len 131072   --tensor-parallel-size 2
```
<details> <summary>Click to expand example</summary>
This vLLM server will be ready for launch when the following logs appear:
INFO:     Started server process [1490]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO 04-22 13:22:12 [loggers.py:87] Engine 000: Avg prompt throughput: 0.0 tokens/s, Avg generation throughput: 0.0 tokens/s, Running: 0 reqs, Waiting: 0 reqs, GPU KV cache usage: 0.0%, Prefix cache hit rate: 0.0%
</details>


 **Start the FastAPI server:**
```python
uvicorn server:app --host 0.0.0.0 --port 8090
```
<details> <summary>Click to expand example</summary>
INFO:     Started server process [2887]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8090 (Press CTRL+C to quit)
</details>

**Run the app:**
```python
python client.py "<prompt>" <session_id
```

* Replace "session_id" with requested user ID to avoid shared conversation history between different users.
* Replace "prompt" with the requested user's input.



**Running Example:**
```python
python client.py "תכתוב סיפור בן 100 מילים" 1
```
