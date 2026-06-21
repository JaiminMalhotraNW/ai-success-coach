import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load the variables from the .env file into os.environ
load_dotenv()

# The permission scope needed to create events
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_calendar_service():
    """Authenticates and returns the Google Calendar API service using the .env JSON string."""
    
    # 1. Get the raw string from your .env file
    creds_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    
    if not creds_str:
        print("DEBUG ERROR: GOOGLE_CREDENTIALS_JSON is completely empty or missing from .env")
        return None
        
    try:
        # 2. Parse the string into a Python dictionary
        creds_dict = json.loads(creds_str)
        
        # 3. Authenticate using the dictionary
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"DEBUG ERROR parsing credentials: {e}")
        return None

def create_calendar_event(student_id: str, session_type: str, reason: str, start_dt, end_dt):
    """
    Creates a 30-minute block on the coach's personal Google Calendar.
    """
    try:
        service = get_calendar_service()
        if not service:
            return False
            
        # Build the event payload
        event = {
            'summary': f"Session: {student_id} - {session_type}",
            'description': f"Student: {student_id}\nReason: {reason}",
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'Asia/Kolkata', 
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
        }

        # IMPORTANT: Replace this with your actual Google email address 
        coach_calendar_id = "danalyst003@gmail.com"

        # Insert the event into your calendar
        created_event = service.events().insert(calendarId=coach_calendar_id, body=event).execute()
        return True

    except Exception as e:
        print(f"DEBUG: Failed to create calendar event: {e}")
        return False