"""LLM-based extraction of lead qualification signals using Gemini."""

import os
import logging
from typing import Dict, Optional
from pydantic import BaseModel, Field
from google import genai

class LeadExtraction(BaseModel):
    business_type: Optional[str] = Field(description="The type of business, e.g. retail, farm, IT services. None if not mentioned.")
    business_vintage: Optional[str] = Field(description="How long the business has been operating, e.g. '2 years'. None if not mentioned.")
    monthly_turnover: Optional[str] = Field(description="The monthly revenue or turnover. None if not mentioned.")
    loan_amount: Optional[str] = Field(description="The requested loan amount. None if not mentioned.")
    city: Optional[str] = Field(description="The city or location of the business or customer. None if not mentioned.")
    qualification_status: str = Field(description="Must be exactly 'qualified', 'not qualified', or 'needs follow-up'. Based on the conversation flow.")
    promise_to_pay_date: Optional[str] = Field(description="The date the customer promised to pay the EMI, if applicable. None if not mentioned.")
    language_spoken: Optional[str] = Field(description="The primary language spoken by the customer, e.g., 'Hindi', 'English'.")
    summary: Optional[str] = Field(description="A brief 1-2 sentence summary of the call outcome.")

def extract_lead_info(transcript: Optional[str]) -> Dict[str, Optional[str]]:
    default_result = {
        "business_type": None,
        "business_vintage": None,
        "monthly_turnover": None,
        "loan_amount": None,
        "city": None,
        "qualification_status": "needs follow-up",
        "promise_to_pay_date": None,
        "language_spoken": None,
        "summary": "No transcript available.",
    }

    if not transcript or not transcript.strip():
        return default_result

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your-gemini-key":
        logging.warning("GEMINI_API_KEY not set. Falling back to default extraction.")
        return default_result

    try:
        client = genai.Client(api_key=api_key)
        prompt = f"Analyze the following call transcript and extract the requested fields. Transcript:\n\n{transcript}"
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': LeadExtraction,
                'temperature': 0.1,
            },
        )
        
        extraction = LeadExtraction.model_validate_json(response.text)
        return extraction.model_dump()
        
    except Exception as e:
        logging.exception(f"LLM extraction failed: {e}")
        default_result["summary"] = f"Extraction failed: {str(e)}"
        return default_result
