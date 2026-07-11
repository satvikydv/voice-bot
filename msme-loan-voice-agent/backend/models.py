"""Pydantic models used by the backend."""

from typing import Optional
from pydantic import BaseModel


class CallRecord(BaseModel):
    call_id: Optional[str] = None
    phone_number: Optional[str] = None
    timestamp: Optional[str] = None
    status: Optional[str] = None
    duration: Optional[int] = None
    transcript: Optional[str] = None
    recording_url: Optional[str] = None
    business_type: Optional[str] = None
    business_vintage: Optional[str] = None
    monthly_turnover: Optional[str] = None
    loan_amount: Optional[str] = None
    city: Optional[str] = None
    qualification_status: Optional[str] = None
