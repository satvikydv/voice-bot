"""Streamlit dashboard for reviewing call activity."""

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

DEFAULT_MONGO_URI = "mongodb://localhost:27017/msme_agent"
DB_NAME = "msme_agent"
COLLECTION_NAME = "calls"

@st.cache_data(show_spinner=False, ttl=5)
def load_data() -> pd.DataFrame:
    mongo_uri = os.getenv("MONGO_URI", DEFAULT_MONGO_URI)
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        db = client.get_database()
        coll = db[COLLECTION_NAME]
        
        cursor = coll.find({}).sort("timestamp", -1)
        data = list(cursor)
        
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        
        # Drop mongo _id column if present
        if "_id" in df.columns:
            df = df.drop(columns=["_id"])
            
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        if df["timestamp"].dt.tz is None:
            df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
        df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
        
        df["date"] = df["timestamp"].dt.date
        df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %I:%M %p")
        
        if "customer_name" in df.columns:
            df["name"] = df["customer_name"].fillna(df["call_id"])
        else:
            df["name"] = df["call_id"]
            
        return df
    except Exception as e:
        st.error(f"Error connecting to MongoDB: {e}")
        return pd.DataFrame()

st.set_page_config(page_title="MSME Loan Voice Agent", layout="wide")

st.title("MSME Loan Voice Agent Dashboard")

data = load_data()
filtered = data.copy()

st.sidebar.header("Initiate Call")
target_phone = st.sidebar.text_input("Phone Number (E.164)", placeholder="+1234567890")
target_name = st.sidebar.text_input("Name (Optional)", placeholder="John Doe")
if st.sidebar.button("Make Call"):
    if not target_phone:
        st.sidebar.error("Please enter a phone number.")
    else:
        try:
            import requests
            payload = {"phone_number": target_phone}
            if target_name:
                payload["name"] = target_name
                
            response = requests.post(
                "http://localhost:8000/call",
                json=payload,
                timeout=10
            )
            if response.status_code == 200:
                st.sidebar.success(f"Call initiated: {response.json().get('call_id')}")
            else:
                st.sidebar.error(f"Failed: {response.text}")
        except Exception as e:
            st.sidebar.error(f"Error connecting to backend: {e}")

st.sidebar.markdown("---")
st.sidebar.header("Filters")

if not data.empty:
    status_filter = st.sidebar.multiselect(
        "Call status",
        sorted(data["status"].dropna().unique().tolist()),
    )

    qualification_filter = st.sidebar.multiselect(
        "Qualification status",
        sorted(data["qualification_status"].dropna().unique().tolist()),
    )

    min_date = data["date"].min()
    max_date = data["date"].max()

    date_range = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]

    if qualification_filter:
        filtered = filtered[filtered["qualification_status"].isin(qualification_filter)]

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        filtered = filtered[(filtered["date"] >= start_date) & (filtered["date"] <= end_date)]


st.subheader("Overview")

col1, col2, col3, col4, col5 = st.columns(5)
total_calls = len(filtered)
completed_calls = (filtered["status"] == "completed").sum() if not filtered.empty and "status" in filtered.columns else 0
missed_calls = (filtered["status"] == "failed").sum() if not filtered.empty and "status" in filtered.columns else 0

# Check the new 'Lead Qualified' structured output boolean
if not filtered.empty and "Lead Qualified" in filtered.columns:
    qualified_leads = (filtered["Lead Qualified"] == True).sum()
else:
    # Fallback to the old regex parser if needed
    qualified_leads = (filtered["qualification_status"] == "qualified").sum() if not filtered.empty and "qualification_status" in filtered.columns else 0

if not filtered.empty and "duration" in filtered.columns:
    avg_duration = filtered["duration"].dropna().mean()
    avg_duration_str = f"{avg_duration:.1f}s" if pd.notna(avg_duration) else "0s"
else:
    avg_duration_str = "0s"

col1.metric("Total Calls", total_calls)
col2.metric("Completed Calls", completed_calls)
col3.metric("Missed / Not Picked", missed_calls)
col4.metric("Qualified Leads", qualified_leads)
col5.metric("Avg Duration", avg_duration_str)


st.subheader("Call Table")

if filtered.empty:
    st.info("No call data available yet. Please initiate a call to populate the dashboard.")
    empty_df = pd.DataFrame(columns=[
        "name",
        "phone_number",
        "status",
        "duration",
        "evaluation",
        "score"
    ])
    st.dataframe(empty_df, use_container_width=True)
else:
    table_df = filtered.copy()
    if "Success Evaluation - Descriptive" in table_df.columns:
        table_df.rename(columns={"Success Evaluation - Descriptive": "evaluation"}, inplace=True)
    elif "qualification_status" in table_df.columns:
        table_df.rename(columns={"qualification_status": "evaluation"}, inplace=True)
        
    if "Success Evaluation - Numeric Scale" in table_df.columns:
        table_df.rename(columns={"Success Evaluation - Numeric Scale": "score"}, inplace=True)
        
    display_cols = [c for c in ["name", "phone_number", "status", "duration", "evaluation", "score"] if c in table_df.columns]
    st.dataframe(table_df[display_cols], use_container_width=True)

st.subheader("Transcript & Evaluation")

if not filtered.empty:
    call_ids = filtered["call_id"].dropna().unique().tolist()
    selected_call = st.selectbox("Select a call", call_ids)

    if selected_call:
        selected_row = filtered[filtered["call_id"] == selected_call].iloc[0]
        
        # Display Structured Data
        standard_keys = {
            "call_id", "phone_number", "customer_name", "name", 
            "timestamp", "status", "duration", 
            "transcript", "recording_url", "business_type", "business_vintage", 
            "monthly_turnover", "loan_amount", "city", "qualification_status", 
            "ended_reason", "date", "_id"
        }
        
        row_dict = selected_row.to_dict()
        structured_info = {k: v for k, v in row_dict.items() if k not in standard_keys and pd.notna(v) and v != ""}
        
        if structured_info:
            st.write("**Structured Outputs & Extra Info**")
            for k, v in structured_info.items():
                if k == "Call Summary":
                    st.info(f"**{k}**: {v}")
                else:
                    st.write(f"- **{k}**: {v}")
            st.write("---")

        st.write("**Transcript**")
        raw_transcript = selected_row.get("transcript")
        
        if pd.isna(raw_transcript) or not raw_transcript:
            st.info("No transcript available.")
        else:
            # Parse the transcript line by line to create a chat interface
            lines = str(raw_transcript).split('\n')
            
            # Simple container to hold the chat
            chat_container = st.container(height=400)
            
            with chat_container:
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    if line.startswith("AI:"):
                        with st.chat_message("assistant"):
                            st.write(line[3:].strip())
                    elif line.startswith("User:"):
                        with st.chat_message("user"):
                            st.write(line[5:].strip())
                    else:
                        # Fallback for unrecognized formats or multiline messages
                        st.write(line)

        recording_url = selected_row.get("recording_url")
        if pd.notna(recording_url) and recording_url:
            st.write("**Recording**")
            st.audio(recording_url)
else:
    st.write("No transcripts available.")
