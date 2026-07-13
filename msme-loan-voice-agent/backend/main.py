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

SECTOR_PROMPTS = {
    "Retail": "You are a friendly and professional voice AI agent representing a premier MSME loan provider. Your goal is to qualify retail business owners for a business loan. Speak clearly, empathetically, and keep your responses conversational and concise. Do not sound like a robot. Please guide the conversation to extract the following information gently: 1. Business Type: What kind of retail store do they run? 2. Business Vintage: How long have they been in business? (Minimum 1 year preferred). 3. Monthly Turnover: What is their average monthly revenue or daily footfall? 4. Loan Amount: How much funding do they need? 5. Purpose: Are they using it for inventory, expansion, or working capital? 6. Location/City: Where is their primary store located? If they refuse to answer a question, politely move to the next one. At the end of the call, thank them for their time and tell them a human representative will follow up if they qualify.",
    "Technology": "You are a professional and sharp voice AI agent representing a premier MSME loan provider. Your goal is to qualify technology businesses and startups for a business loan. Speak with a professional, B2B tone. Be concise, respectful of their time, and knowledgeable. Please guide the conversation to extract the following information gently: 1. Business Type: Are they a SaaS, IT services, or hardware company? 2. Business Vintage: How long have they been operating? 3. Revenue Model: What is their Monthly Recurring Revenue (MRR) or annual run rate? 4. Loan Amount: How much funding are they seeking? 5. Purpose: Is the capital for software development, marketing, server costs, or hiring? 6. Location/City: Where is their company headquartered? If they ask about interest rates, tell them rates are determined dynamically based on their profile during the final approval stage. Thank them for their time and let them know the next steps.",
    "Agriculture": "You are a warm, patient, and respectful voice AI agent representing a premier MSME loan provider. Your goal is to qualify farmers and agricultural businesses for a business loan. Speak slowly, clearly, and use simple language. Avoid complex financial jargon. Build trust. Please guide the conversation to extract the following information gently: 1. Business Type: Do they run a farm, sell equipment, or trade crops? 2. Business Vintage: How many crop cycles or years have they been operating? 3. Income Profile: What is their seasonal income or average annual turnover? 4. Loan Amount: How much money do they need? 5. Purpose: Is it for seeds, tractors, irrigation, or storage? 6. Location/City: Which region or district are they farming in? Show empathy regarding weather or seasonal challenges if they mention them. Conclude by thanking them and assuring them that a local representative will reach out soon.",
}

class CallRequest(BaseModel):
    phone_number: str
    name: Optional[str] = None
    sector: Optional[str] = None

@app.post("/call")
async def initiate_call(request: CallRequest) -> JSONResponse:
    api_key = os.getenv("VAPI_API_KEY")
    phone_number_id = os.getenv("PHONE_NUMBER_ID")

    sector_assistant_map = {
        "Retail": os.getenv("RETAIL_ASSISTANT_ID"),
        "Technology": os.getenv("TECH_ASSISTANT_ID"),
        "Agriculture": os.getenv("AGRI_ASSISTANT_ID"),
    }
    
    assistant_id = os.getenv("ASSISTANT_ID")
    if request.sector and request.sector in sector_assistant_map and sector_assistant_map[request.sector]:
        assistant_id = sector_assistant_map[request.sector]

    if not api_key or not assistant_id or not phone_number_id:
        raise HTTPException(status_code=500, detail="Missing Vapi configuration in environment variables. Check ASSISTANT_ID or sector-specific IDs.")

    try:
        customer_data = {"number": request.phone_number}
        if request.name:
            customer_data["name"] = request.name

        payload = {
            "assistantId": assistant_id,
            "phoneNumberId": phone_number_id,
            "customer": customer_data,
        }

        if request.sector and request.sector in SECTOR_PROMPTS:
            payload["assistantOverrides"] = {
                "systemPrompt": SECTOR_PROMPTS[request.sector]
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
