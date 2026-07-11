# MSME Loan Voice Agent

Backend and dashboard for qualifying MSME loan leads with Vapi voice calls.

## Project Structure

```
msme-loan-voice-agent/
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── webhook_handler.py
│   ├── qualification_parser.py
│   └── make_call.py
├── dashboard/
│   └── streamlit_app.py
├── requirements.txt
└── .env
```

## Setup & Execution

### 1. Install Dependencies
Create a virtual environment (optional) and install the python packages:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root `msme-loan-voice-agent` directory with the following variables:
```env
VAPI_API_KEY=your_api_key_here
ASSISTANT_ID=your_assistant_id
PHONE_NUMBER_ID=your_vapi_phone_number_id
MONGO_URI=mongodb://localhost:27017/msme_agent
```

### 3. Start the Database (MongoDB)
Start the local MongoDB instance using Docker:
```bash
docker-compose up -d
```

### 4. Run the Backend (FastAPI)
Start the backend server on port 8000:
```bash
uvicorn backend.main:app --reload --port 8000
```

### 5. Expose the Webhook Server
Expose your local port 8000 to the internet so Vapi can send webhooks to it:
```bash
ngrok http 8000
```
*Note: Update your Vapi dashboard Webhook URL to point to `HTTPS://<your-ngrok-url>/vapi-webhook`*

### 6. Run the Dashboard (Streamlit)
In a separate terminal, start the Streamlit UI:
```bash
streamlit run dashboard/streamlit_app.py
```

### 7. Trigger a Call
You can trigger a call in three ways:
1. Directly from the **Streamlit Dashboard** sidebar.
2. Using the CLI script:
   ```bash
   python backend/make_call.py --phone +11234567890
   ```
3. Making a POST request to your local API:
   ```bash
   curl -X POST http://localhost:8000/call \
        -H "Content-Type: application/json" \
        -d '{"phone_number": "+11234567890", "name": "John Doe"}'
   ```
