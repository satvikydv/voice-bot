"""Streamlit dashboard for reviewing call activity."""

import os
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px
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

st.set_page_config(page_title="MSME Loan Voice Agent", layout="wide", page_icon="📞")

st.markdown("""
<style>
    .stMetric {
        background-color: #1E293B;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5), 0 2px 4px -1px rgba(0, 0, 0, 0.3);
        border: 1px solid #334155;
    }
    .stMetric label {
        color: #94A3B8 !important;
        font-weight: 600;
        font-size: 1rem;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #F8FAFC !important;
        font-weight: 700;
    }
    .chat-bubble-ai {
        background-color: #1E293B;
        padding: 10px 15px;
        border-radius: 15px;
        margin-bottom: 10px;
        max-width: 80%;
        color: #F8FAFC;
    }
    .chat-bubble-user {
        background-color: #3B82F6;
        padding: 10px 15px;
        border-radius: 15px;
        margin-bottom: 10px;
        max-width: 80%;
        margin-left: auto;
        color: #F8FAFC;
    }
</style>
""", unsafe_allow_html=True)

st.title("📞 Universal Financial Voice Agent")

data = load_data()
filtered = data.copy()

st.sidebar.header("🚀 Initiate Call")
target_phone = st.sidebar.text_input("Phone Number (E.164)", placeholder="+1234567890")
target_name = st.sidebar.text_input("Name (Optional)", placeholder="John Doe")
usecase = st.sidebar.selectbox("Use Case", ["None", "Loan Recovery", "Gold Loan", "Motor Loan", "MSME Loan"])
if st.sidebar.button("Make Call", use_container_width=True):
    if not target_phone:
        st.sidebar.error("Please enter a phone number.")
    else:
        try:
            import requests
            payload = {"phone_number": target_phone}
            if target_name:
                payload["name"] = target_name
            if usecase != "None":
                payload["usecase"] = usecase
                
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
st.sidebar.header("🔍 Filters")

if not data.empty:
    status_filter = st.sidebar.multiselect(
        "Call status",
        sorted(data["status"].dropna().unique().tolist()),
    )

    if "qualification_status" in data.columns:
        qual_options = sorted(data["qualification_status"].dropna().unique().tolist())
    else:
        qual_options = []
        
    qualification_filter = st.sidebar.multiselect(
        "Qualification status",
        qual_options,
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


st.subheader("📊 Overview")

col1, col2, col3, col4, col5 = st.columns(5)
total_calls = len(filtered)
completed_calls = (filtered["status"] == "completed").sum() if not filtered.empty and "status" in filtered.columns else 0
missed_calls = (filtered["status"] == "failed").sum() if not filtered.empty and "status" in filtered.columns else 0

if not filtered.empty and "Lead Qualified" in filtered.columns:
    qualified_leads = (filtered["Lead Qualified"] == True).sum()
else:
    qualified_leads = (filtered["qualification_status"] == "qualified").sum() if not filtered.empty and "qualification_status" in filtered.columns else 0

if not filtered.empty and "duration" in filtered.columns:
    avg_duration = filtered["duration"].dropna().mean()
    avg_duration_str = f"{avg_duration:.1f}s" if pd.notna(avg_duration) else "0s"
else:
    avg_duration_str = "0s"

with col1: st.metric("Total Calls", total_calls)
with col2: st.metric("Completed Calls", completed_calls)
with col3: st.metric("Missed / Not Picked", missed_calls)
with col4: st.metric("Qualified Leads", qualified_leads)
with col5: st.metric("Avg Duration", avg_duration_str)

st.markdown("<br>", unsafe_allow_html=True)
st.subheader("📈 Analytics")

if not filtered.empty:
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        # Call Volume Line Chart
        daily_calls = filtered.groupby('date').size().reset_index(name='count')
        fig_line = px.line(daily_calls, x='date', y='count', title='Call Volume Over Time', markers=True, color_discrete_sequence=['#FACC15'])
        fig_line.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#F8FAFC')
        st.plotly_chart(fig_line, use_container_width=True)
    
    with chart_col2:
        # Status Breakdown Pie Chart
        status_counts = filtered['status'].value_counts().reset_index()
        status_counts.columns = ['status', 'count']
        fig_pie = px.pie(status_counts, values='count', names='status', title='Call Status Distribution', hole=0.4, color_discrete_sequence=px.colors.sequential.Plasma)
        fig_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#F8FAFC')
        st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.info("No analytics data available.")


st.markdown("---")
st.subheader("📝 Call Table")

if filtered.empty:
    st.info("No call data available yet. Please initiate a call to populate the dashboard.")
    empty_df = pd.DataFrame(columns=[
        "name", "phone_number", "status", "duration", "evaluation", "score"
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

st.markdown("---")
st.subheader("💬 Transcript & Evaluation")

if not filtered.empty:
    call_ids = filtered["call_id"].dropna().unique().tolist()
    selected_call = st.selectbox("Select a call to review", call_ids)

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
        
        col_struct, col_trans = st.columns([1, 2])
        
        with col_struct:
            st.markdown("#### **Data Extracted**")
            if structured_info:
                for k, v in structured_info.items():
                    if k == "Call Summary":
                        st.info(f"**{k}**: {v}")
                    else:
                        st.markdown(f"**{k}**: {v}")
            else:
                st.write("No extra structured data.")
                
            recording_url = selected_row.get("recording_url")
            if pd.notna(recording_url) and recording_url:
                st.markdown("#### **Recording**")
                st.audio(recording_url)

        with col_trans:
            st.markdown("#### **Transcript**")
            raw_transcript = selected_row.get("transcript")
            
            if pd.isna(raw_transcript) or not raw_transcript:
                st.info("No transcript available.")
            else:
                lines = str(raw_transcript).split('\n')
                chat_container = st.container(height=500)
                
                with chat_container:
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                            
                        if line.startswith("AI:"):
                            st.markdown(f'<div class="chat-bubble-ai">🤖 <b>AI:</b> {line[3:].strip()}</div>', unsafe_allow_html=True)
                        elif line.startswith("User:"):
                            st.markdown(f'<div class="chat-bubble-user">👤 <b>User:</b> {line[5:].strip()}</div>', unsafe_allow_html=True)
                        else:
                            st.write(line)
else:
    st.write("No transcripts available.")
