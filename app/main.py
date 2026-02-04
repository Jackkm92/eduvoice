import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """
    Schema for incoming chat requests. The frontend sends a JSON
    payload containing the user's message. Additional fields can
    be added later (e.g., conversation ID) without breaking the API.
    """
    message: str


app = FastAPI()

# Allow CORS so that the browser can call the API from the same origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FOUNDATION_AGENT_ENDPOINT = os.getenv("FOUNDATION_AGENT_ENDPOINT")
FOUNDATION_AGENT_API_KEY = os.getenv("FOUNDATION_AGENT_API_KEY")


@app.post("/api/chat")
def chat(message: ChatMessage):
    """
    Send the user's message to the existing Microsoft AI Foundry agent
    and return the agent's response. The endpoint and API key must
    be configured via environment variables. If the agent call fails,
    raise a 502 error.
    """
    if not FOUNDATION_AGENT_ENDPOINT or not FOUNDATION_AGENT_API_KEY:
        raise HTTPException(status_code=500, detail="Foundry agent configuration is missing.")

    # Prepare the payload for the Foundry agent. The exact schema
    # depends on the agent API. Here we assume it accepts a JSON
    # body with a `message` field.
    payload = {"message": message.message}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {FOUNDATION_AGENT_API_KEY}",
    }
    try:
        response = requests.post(FOUNDATION_AGENT_ENDPOINT, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        # Log the error and return a generic error to the client
        raise HTTPException(status_code=502, detail="Error communicating with AI agent") from e

    # We assume the agent response JSON has a 'reply' field containing the assistant's text.
    # Adjust this according to the actual API response schema.
    agent_reply = data.get("reply") or data.get("response") or data
    return {"reply": agent_reply}


@app.get("/")
def get_index():
    """
    Serve the main HTML file. FastAPI will look up the file in the
    static directory relative to this file. Adjust the path if you
    reorganise the project.
    """
    file_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    return FileResponse(file_path)


@app.get("/static/{file_path:path}")
def static_files(file_path: str):
    """
    Serve static files such as CSS and JavaScript. Azure App Service
    will handle serving static content automatically when configured,
    but this route makes local development easy.
    """
    absolute_path = os.path.join(os.path.dirname(__file__), "static", file_path)
    return FileResponse(absolute_path)