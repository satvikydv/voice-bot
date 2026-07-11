# Troubleshooting and Implementation Log

This document summarizes the primary challenges encountered while building the Vapi integration and Streamlit Dashboard, along with the solutions deployed.

## 1. Difficulties Parsing Vapi Webhook Payloads
- **Problem**: Vapi's webhook `POST` body structure was inconsistent. In some events, the core call data was nested under `message.call`, while in others, it was under `call` or `data.call`. This led to empty records and skipped webhook processing logs.
- **Solution**: Implemented a robust `_normalize_payload` function in `backend/webhook_handler.py`. This function checks the payload structure dynamically and flattens out the actual Call Object, allowing the webhook handler to extract keys predictably regardless of the incoming webhook event type.

## 2. Invalid Data Types during Database Insertion
- **Problem**: The Vapi payload occasionally sends the `phoneNumber` or `customer` phone number as a nested dictionary (e.g. `{"number": "+1..."}`) instead of a raw string. When saving to the original SQLite database, this was causing generic `sqlite3.ProgrammingError` binding errors.
- **Solution**: Added type-checking assertions to safely extract just the `.get("number")` string if the parser detects a dictionary format.

## 3. SQLite Limitations on Local Environment
- **Problem**: The windows development environment lacked the `sqlite3` CLI, making debugging difficult. Furthermore, a relational database structure made saving dynamic, changing schemas—like new AI-generated custom labels—very tedious.
- **Solution**: Completely migrated the application database to **MongoDB**.
  - Wrote a new `docker-compose.yml` file to instantly provision a local MongoDB container.
  - Rewrote the `backend/database.py` interface using `pymongo`.
  - MongoDB seamlessly stores flexible BSON document properties natively, fitting the dynamic Vapi payloads perfectly.

## 4. Application Startup Crash (PyMongo Index Syntax)
- **Problem**: During startup, FastAPI crashed due to a `pymongo` syntax error when calling `create_index(..., descending=True)`.
- **Solution**: Corrected the syntax to properly create a descending index on timestamps using the standard PyMongo tuple configuration: `[("timestamp", -1)]`.

## 5. Webhook "Call Status" Sticking to 'queued'
- **Problem**: Calls successfully initiated and terminated on Vapi were continually displaying as `"queued"` on the dashboard. The raw Vapi `status-update` stream did not cleanly deliver the absolute final state in a friendly variable.
- **Solution**: Adjusted the webhook parser to monitor the final `end-of-call-report` event. At the end of a call, the system now reads the raw `endedReason` (e.g., `"customer-did-not-answer"`, `"voicemail"`, `"completed"`) and overrides the database `status` to precisely reflect whether a call was `completed` or `failed`.

## 6. Accessing AI-Generated Structured Outputs
- **Problem**: Extracting Vapi's dynamic success evaluations manually out of the transcript text was nearly impossible. User configured specific extraction modules in Vapi (like "Success Evaluation" or "Lead Qualified").
- **Solution**: Found that Vapi sends these insights nested inside `artifact.structuredOutputs`. Built a loop in the webhook handler to iterate over the arbitrary dictionary keys, dynamically constructing a flat dictionary mapping `{ "Metric Name": "Result value" }`—all of which gets auto-inserted into the flexible MongoDB instance and retrieved flawlessly by the Streamlit dashboard on refresh.

## 7. Adding Optional Customer Names
- **Problem**: The dashboard only displayed `call_id`s, lacking context on who exactly the voice agent was talking to.
- **Solution**: Updated the FastAPI `/call` endpoint to accept an optional `name` payload and feed it into Vapi's `customer` property during initiation. Extracted this `customer.name` from the returning webhooks and wired it into the dashboard using a fallback UI variable (`name` defaults to `customer_name` if present, else drops back to `call_id`).

## 8. Dashboard Dashboard Times Displaying as "Year 1970" / UTC
- **Problem**: The raw timestamps captured in MongoDB were natively stored in UTC and Pandas was failing to cleanly parse them or displayed an epoch date of 1970.
- **Solution**: Reconfigured the Streamlit data-loader pipeline: `pd.to_datetime` errors forced to `coerce`, localized naked timestamps explicitly to `"UTC"`, and precisely translated them directly to `"Asia/Kolkata"` (IST), formatted into `%Y-%m-%d %I:%M %p` for easy legibility.
