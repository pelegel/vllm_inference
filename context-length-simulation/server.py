from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import httpx
import asyncio
import json

app = FastAPI()

VLLM_API_URL = "http://localhost:8000/v1/chat/completions"
MODEL_NAME = "gaunernst/gemma-3-12b-it-int4-awq"

async def stream_vllm_response(messages):
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": True
    }

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", VLLM_API_URL, headers=headers, json=payload) as response:
            async for line in response.aiter_lines():
                if line.strip() == "" or not line.startswith("data:"):
                    continue
                chunk = line.removeprefix("data:").strip()
                if chunk == "[DONE]":
                    yield "data: [DONE]\n\n"
                    break
                yield f"data: {chunk}\n\n"
                await asyncio.sleep(0)  # Yield control to event loop without delay

@app.post("/stream")
async def stream_endpoint(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    return StreamingResponse(stream_vllm_response(messages), media_type="text/event-stream")
