"""Rule-based extraction of lead qualification signals."""

import re
from typing import Dict, Optional, Tuple

UNIT_MULTIPLIERS = {
    "k": 1_000,
    "thousand": 1_000,
    "lakh": 100_000,
    "lakhs": 100_000,
    "crore": 10_000_000,
    "crores": 10_000_000,
    "m": 1_000_000,
    "million": 1_000_000,
}


def _clean_text(text: str) -> str:
    return " ".join(text.lower().split())


def _extract_amount(text: str, keywords: Tuple[str, ...]) -> Tuple[Optional[str], Optional[float]]:
    pattern = rf"(?:{'|'.join(keywords)})\s*(?:is|of|around|about|approx(?:imately)?|=)?\s*([0-9]+(?:\.[0-9]+)?)\s*(lakh|lakhs|crore|crores|thousand|million|k|m)?"
    match = re.search(pattern, text)
    if not match:
        return None, None
    value = float(match.group(1))
    unit = match.group(2) or ""
    multiplier = UNIT_MULTIPLIERS.get(unit, 1)
    normalized = value * multiplier
    label = f"{match.group(1)} {unit}".strip()
    return label, normalized


def _extract_years(text: str) -> Tuple[Optional[str], Optional[float]]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(year|years|yr|yrs|month|months)", text)
    if not match:
        return None, None
    value = float(match.group(1))
    unit = match.group(2)
    years = value / 12 if "month" in unit else value
    label = f"{match.group(1)} {unit}"
    return label, years


def _extract_business_type(text: str) -> Optional[str]:
    patterns = [
        r"business type is ([a-z\s]+)",
        r"we are in the ([a-z\s]+) business",
        r"we run a ([a-z\s]+) business",
        r"we run a ([a-z\s]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def _extract_city(text: str) -> Optional[str]:
    patterns = [
        r"based in ([a-z\s]+)",
        r"located in ([a-z\s]+)",
        r"from ([a-z\s]+)",
        r"in ([a-z\s]+) city",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def extract_lead_info(transcript: Optional[str]) -> Dict[str, Optional[str]]:
    if not transcript:
        return {
            "business_type": None,
            "business_vintage": None,
            "monthly_turnover": None,
            "loan_amount": None,
            "city": None,
            "qualification_status": "needs follow-up",
        }

    text = _clean_text(transcript)
    business_type = _extract_business_type(text)
    business_vintage_label, business_vintage_years = _extract_years(text)
    turnover_label, turnover_value = _extract_amount(
        text,
        ("monthly turnover", "monthly revenue", "turnover", "revenue"),
    )
    loan_label, loan_value = _extract_amount(
        text,
        ("loan amount", "loan", "need", "require"),
    )
    city = _extract_city(text)

    if turnover_value is None or business_vintage_years is None or loan_value is None:
        qualification_status = "needs follow-up"
    elif business_vintage_years >= 1 and turnover_value >= 200_000 and loan_value <= 5_000_000:
        qualification_status = "qualified"
    else:
        qualification_status = "not qualified"

    return {
        "business_type": business_type,
        "business_vintage": business_vintage_label,
        "monthly_turnover": turnover_label,
        "loan_amount": loan_label,
        "city": city,
        "qualification_status": qualification_status,
    }
