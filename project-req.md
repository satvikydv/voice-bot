I am building a project for a voice AI agent that qualifies MSME business loan leads using the Vapi voice agent platform.

I want you to generate the backend and frontend code for the following system.

Tech stack:
Backend:

* Python
* FastAPI
* SQLite (simple local database)
* Vapi webhook integration

Frontend:

* Streamlit dashboard

Goal of the system:
The Vapi voice assistant will make outbound calls to users and qualify them for MSME business loans. After each call, Vapi will send webhook events containing call data and transcripts to our backend. The backend should process and store this data. The Streamlit dashboard should display call analytics and allow stakeholders to review conversations.

System architecture:
User Phone → Vapi Voice Agent → Webhook → FastAPI Backend → SQLite Database → Streamlit Dashboard

Backend requirements:

1. FastAPI server
   Create a FastAPI app with the following endpoints:

POST /vapi-webhook
Receives webhook events from Vapi.

The webhook payload may contain fields like:

* callId
* assistantId
* phoneNumber
* status (completed, failed, busy)
* transcript
* messages
* duration
* recordingUrl

The backend should:

* Parse the webhook payload
* Extract relevant information
* Store it in the database

2. Database schema

Create a SQLite database with a table named calls.

Fields:

* id (primary key)
* call_id
* phone_number
* timestamp
* status
* duration
* transcript
* recording_url
* business_type
* business_vintage
* monthly_turnover
* loan_amount
* city
* qualification_status

3. Lead qualification extraction

Implement a function that parses the transcript and extracts:

* business type
* business vintage
* monthly turnover
* loan amount requested
* city
* qualification status (qualified, not qualified, needs follow-up)

Use simple rule-based extraction or regex.

4. Call initiation script

Create a Python script called make_call.py that uses the Vapi API to trigger an outbound call.

Inputs:

* VAPI_API_KEY
* ASSISTANT_ID
* target phone number

The script should send a POST request to the Vapi API to start a call.

5. Logging

Log all webhook events and errors.

Frontend (Streamlit) requirements:

Create a Streamlit dashboard that reads from the SQLite database.

Dashboard features:

1. Overview metrics
   Display:

* total calls
* completed calls
* failed calls
* qualified leads

2. Call table

Show a table with:

* call_id
* phone_number
* status
* duration
* qualification_status
* timestamp

3. Transcript viewer

Allow clicking a call to view the full transcript.

4. Audio playback

If recording_url exists, allow playback in Streamlit.

5. Analytics charts

Create charts for:

* calls per day
* success rate
* qualified vs not qualified leads

6. Filters

Allow filtering by:

* qualification status
* date range
* call status

Project structure:

msme-loan-voice-agent/
│
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── webhook_handler.py
│   ├── qualification_parser.py
│   └── make_call.py
│
├── dashboard/
│   └── streamlit_app.py
│
├── requirements.txt
└── README.md

Requirements:

* Use clean, modular Python code
* Include comments explaining each component
* Ensure the webhook endpoint correctly handles JSON payloads from Vapi
* Provide instructions to run backend and dashboard locally

Also generate a requirements.txt file containing all required dependencies.
