import os
import json
import streamlit as st
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

st.title("📅 Standalone Calendar Test")

# 1. Manually trigger python-dotenv to load your .env file
load_dotenv()

# 2. Add your actual email here!
COACH_EMAIL = "danalyst003@gmail.com" 

def test_calendar_connection():
    st.write("---")
    st.write("### Diagnostics:")
    
    # Check if we can find the .env variable
    creds_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    
    if not creds_str:
        st.error("❌ `GOOGLE_CREDENTIALS_JSON` was not found in your environment variables.")
        st.write("Make sure your `.env` file is in the same folder as `test.py` and the variable name matches exactly.")
        return False
        
    st.success("✅ Found `GOOGLE_CREDENTIALS_JSON` in environment.")
    
    try:
        # Try to parse the JSON string
        creds_dict = json.loads(creds_str)
        st.success("✅ Successfully parsed JSON credentials.")
        
        # Try to build the service
        SCOPES = ['https://www.googleapis.com/auth/calendar.events']
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        st.success("✅ Successfully authenticated with Google API.")
        
        # Try to create a test event
        now = datetime.now()
        start_dt = now + timedelta(hours=1)
        end_dt = start_dt + timedelta(minutes=30)
        
        event = {
            'summary': "Connection Test",
            'description': "Testing from standalone script.",
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
        }
        
        with st.spinner("Pushing event to calendar..."):
            created_event = service.events().insert(calendarId=COACH_EMAIL, body=event).execute()
            
        st.success(f"✅ Success! Created event ID: `{created_event.get('id')}`")
        return True
        
    except json.JSONDecodeError as e:
        st.error(f"❌ Failed to parse JSON. Your `.env` string might be malformed. Error: {e}")
        return False
    except Exception as e:
        st.error(f"❌ Google API Error: {e}")
        return False

if st.button("Run Diagnostics"):
    test_calendar_connection()