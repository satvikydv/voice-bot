"""CLI tool to trigger outbound Vapi calls."""

import argparse
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(description="Initiate an outbound Vapi call.")
    parser.add_argument("--phone", required=True, help="Target phone number in E.164 format")
    args = parser.parse_args()

    api_key = os.getenv("VAPI_API_KEY")
    assistant_id = os.getenv("ASSISTANT_ID")
    phone_number_id = os.getenv("PHONE_NUMBER_ID")

    if not api_key or not assistant_id or not phone_number_id:
        print("Missing VAPI_API_KEY, ASSISTANT_ID, or PHONE_NUMBER_ID in environment.")
        return 1

    response = requests.post(
        "https://api.vapi.ai/call",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "assistantId": assistant_id,
            "phoneNumberId": phone_number_id,
            "customer": {"number": args.phone},
        },
        timeout=30,
    )

    if response.status_code >= 300:
        print(f"Call failed: {response.status_code} {response.text}")
        return 1

    call = response.json()
    print(f"Call initiated: {call.get('id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
