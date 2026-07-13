"""FastAPI entrypoint for Vapi webhooks."""

import logging
import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .database import init_db
from .webhook_handler import handle_vapi_webhook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

app = FastAPI(title="MSME Loan Voice Agent API")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/vapi-webhook")
async def vapi_webhook(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
    except Exception as exc:
        logging.exception("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    record = handle_vapi_webhook(payload)
    return JSONResponse({"status": "ok", "call_id": record.get("call_id")})


from pydantic import BaseModel
import os
import requests
from typing import Optional

import pathlib

def load_prompt(usecase: str) -> Optional[str]:
    filename = usecase.lower().replace(" ", "_") + ".md"
    filepath = pathlib.Path(__file__).parent / "prompts" / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return None

class CallRequest(BaseModel):
    phone_number: str
    name: Optional[str] = None
    usecase: Optional[str] = None

@app.post("/call")
async def initiate_call(request: CallRequest) -> JSONResponse:
    api_key = os.getenv("VAPI_API_KEY")
    phone_number_id = os.getenv("PHONE_NUMBER_ID")

    usecase_assistant_map = {
        "Loan Recovery": os.getenv("RECOVERY_ASSISTANT_ID"),
        "Gold Loan": os.getenv("GOLD_ASSISTANT_ID"),
        "Motor Loan": os.getenv("MOTOR_ASSISTANT_ID"),
        "MSME Loan": os.getenv("MSME_ASSISTANT_ID"),
    }
    
    assistant_id = os.getenv("ASSISTANT_ID")
    if request.usecase and request.usecase in usecase_assistant_map and usecase_assistant_map[request.usecase]:
        assistant_id = usecase_assistant_map[request.usecase]

    if not api_key or not assistant_id or not phone_number_id:
        raise HTTPException(status_code=500, detail="Missing Vapi configuration in environment variables. Check ASSISTANT_ID or usecase-specific IDs.")

    try:
        customer_data = {"number": request.phone_number}
        if request.name:
            customer_data["name"] = request.name

        payload = {
            "assistantId": assistant_id,
            "phoneNumberId": phone_number_id,
            "customer": customer_data,
        }

        if request.usecase:
            prompt = load_prompt(request.usecase)
            if prompt:
                payload["assistantOverrides"] = {
                    "systemPrompt": prompt
                }

        response = requests.post(
            "https://api.vapi.ai/call",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        call_data = response.json()
        return JSONResponse({"status": "success", "call_id": call_data.get("id")})
    except Exception as exc:
        logging.exception("Failed to initiate call")
        raise HTTPException(status_code=500, detail=str(exc))
