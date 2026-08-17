Here are the commands to run the project. The stack is **FastAPI backend + Streamlit dashboard + MongoDB (Docker)**. Run each step in order:

---

### 1. Install dependencies
```powershell
cd msme-loan-voice-agent
pip install -r requirements.txt
```

### 2. Start MongoDB (Docker)
```powershell
docker-compose up -d
```

### 3. Start the FastAPI backend (Terminal 1)
```powershell
uvicorn backend.main:app --reload --port 8000
```

### 4. Expose webhook via ngrok (Terminal 2)
```powershell
ngrok http 8000
```
> After this, copy the HTTPS URL and update your Vapi dashboard's **Webhook URL** to `https://<your-ngrok-url>/vapi-webhook`

### 5. Start the Streamlit dashboard (Terminal 3)
```powershell
streamlit run dashboard/streamlit_app.py
```

---

### Trigger a call (optional)
From CLI:
```powershell
python backend/make_call.py --phone +11234567890
```
Or from the Streamlit sidebar directly.

---