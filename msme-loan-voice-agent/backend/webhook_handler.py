"""Parse Vapi webhook payloads and persist call data."""

import csv
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .database import insert_call
from .qualification_parser import extract_lead_info

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CSV_PATH = BASE_DIR / "data" / "calls.csv"


def _resolve_csv_path() -> Path:
    env_path = os.getenv("CALLS_CSV_PATH")
    if env_path:
        path = Path(env_path).expanduser()
        if not path.is_absolute():
            path = (BASE_DIR / path).resolve()
        return path
    return DEFAULT_CSV_PATH


CSV_PATH = _resolve_csv_path()


def _append_call_to_csv(record: Dict[str, Any]) -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "call_id",
        "phone_number",
        "timestamp",
        "status",
        "duration",
        "transcript",
        "recording_url",
        "business_type",
        "business_vintage",
        "monthly_turnover",
        "loan_amount",
        "city",
        "qualification_status",
    ]
    write_header = not CSV_PATH.exists()
    with CSV_PATH.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow({name: record.get(name) for name in fieldnames})


def _extract_transcript(payload: Dict[str, Any]) -> Optional[str]:
    transcript = payload.get("transcript")
    if isinstance(transcript, str) and transcript.strip():
        return transcript

    messages = payload.get("messages")
    if isinstance(messages, list):
        parts = []
        for message in messages:
            role = message.get("role")
            content = message.get("content") or message.get("text")
            if content:
                if role:
                    parts.append(f"{role}: {content}")
                else:
                    parts.append(str(content))
        if parts:
            return "\n".join(parts)

    return None


def _normalize_payload(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if isinstance(payload.get("message"), dict):
        msg = payload["message"]
        call_data = dict(msg)
        if isinstance(msg.get("call"), dict):
            call_data.update(msg["call"])
        return call_data, msg
    if isinstance(payload.get("call"), dict):
        return payload.get("call", {}), payload
    if isinstance(payload.get("data"), dict) and isinstance(payload["data"].get("call"), dict):
        return payload["data"]["call"], payload
    if isinstance(payload.get("payload"), dict) and isinstance(payload["payload"].get("call"), dict):
        return payload["payload"]["call"], payload
    if isinstance(payload.get("data"), dict):
        return payload.get("data", {}), payload
    return payload, payload


def handle_vapi_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    call_data, raw_payload = _normalize_payload(payload)
    event_type = raw_payload.get("type") or raw_payload.get("event")
    logging.info(
        "Webhook received keys=%s eventType=%s",
        sorted(raw_payload.keys()),
        event_type,
    )

    call_id = call_data.get("callId") or call_data.get("id")
    phone_number = call_data.get("phoneNumber")
    if isinstance(phone_number, dict):
        phone_number = phone_number.get("number")
        
    customer = call_data.get("customer", {})
    customer_name = None
    if isinstance(customer, dict):
        if not phone_number:
            phone_number = customer.get("number")
        customer_name = customer.get("name")

    timestamp = call_data.get("timestamp") or call_data.get("endedAt") or call_data.get("createdAt")
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()

    transcript = _extract_transcript(call_data)
    lead_info = extract_lead_info(transcript)

    # Calculate status based on event type and endedReason
    status = call_data.get("status")
    ended_reason = call_data.get("endedReason")
    
    if event_type == "end-of-call-report":
        if ended_reason in ["customer-did-not-answer", "silence-timed-out", "voicemail", "pipeline-error"]:
            status = "failed"
        else:
            status = "completed"

    # Extract dynamic structured outputs from the artifact
    structured_data = {}
    artifact = raw_payload.get("artifact", {})
    if "structuredOutputs" not in artifact:
        # Sometimes artifact is inside call_data
        artifact = call_data.get("artifact", {})
    
    structured_outputs = artifact.get("structuredOutputs", {})
    if isinstance(structured_outputs, dict):
        for uid, output in structured_outputs.items():
            name = output.get("name")
            result = output.get("result")
            if name:
                structured_data[name] = result

    # Also capture summary if present
    summary = call_data.get("summary") or artifact.get("summary")
    if summary and "Call Summary" not in structured_data:
        structured_data["Call Summary"] = summary

    # Duration calculation
    duration_secs = call_data.get("durationSeconds") or call_data.get("duration")

    record = {
        "call_id": call_id,
        "phone_number": phone_number,
        "customer_name": customer_name,
        "timestamp": timestamp,
        "status": status,
        "ended_reason": ended_reason,
        "duration": duration_secs,
        "transcript": transcript,
        "recording_url": call_data.get("recordingUrl") or call_data.get("recording_url"),
        **lead_info,
        **structured_data
    }

    has_data = any(
        record.get(field)
        for field in ("call_id", "phone_number", "status", "transcript", "recording_url")
    )
    if not has_data:
        logging.warning("Skipping empty webhook payload")
        return record

    insert_call(record)
    
    # Still write core fields to CSV for backwards compatibility if needed
    _append_call_to_csv(record)
    
    logging.info("Stored call webhook call_id=%s status=%s", call_id, record["status"])
    return record
