# Hosting Gemma3 27b model using vLLM #

This inference is based on "gaunernst/gemma-3-27b-it-int4-awq" model from HuggingFace.


**To run the server:**
```
# python3 -m vllm.entrypoints.openai.api_server --model gaunernst/gemma-3-27b-it-int4-awq --port 8000
vllm serve "gaunernst/gemma-3-27b-it-int4-awq"   --max-model-len 131072   --tensor-parallel-size 2
uvicorn server:app --host 0.0.0.0 --port 8090
```

**To call the server:**
```
python client.py "<prompt>"
```

* Replace "session_id" with requested user ID to avoid shared conversation history between different users.
* Replace "prompt" with the requested user's input.



**Running Example:**
```
python client.py "מי אתה?"
```
