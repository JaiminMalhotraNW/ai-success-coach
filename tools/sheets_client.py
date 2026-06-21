import os
import json
import gspread
from langchain_core.tools import tool
from datetime import datetime

def get_client_and_url():
    """Helper function to authenticate and return the client and url."""
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    sheet_url = os.getenv("GOOGLE_SHEET_URL")
    if not creds_json or not sheet_url:
        raise ValueError("Google credentials or Sheet URL not found in .env")
    
    creds_dict = json.loads(creds_json)
    client = gspread.service_account_from_dict(creds_dict)
    return client, sheet_url

def get_tab(tab_name):
    """Helper to open a specific tab by name."""
    client, url = get_client_and_url()
    return client.open_by_url(url).worksheet(tab_name)

def get_roster():
    """Fetches the student roster for the UI dropdown."""
    try:
        return get_tab("roster").get_all_records()
    except Exception as e:
        print(f"Error fetching roster: {e}")
        return []

@tool
def get_student_scores(student_id: str) -> str:
    """Use this tool to fetch the recent academic scores for a specific student_id."""
    try:
        records = get_tab("exam_scores").get_all_records()
        student_records = [r for r in records if str(r.get("student_id", "")) == student_id]
        if not student_records:
            return f"No score records found for {student_id}."
        
        output = [f"- {r['subject']}: {r['score']}/{r['max_score']} (on {r['date']})" for r in student_records]
        return "\n".join(output)
    except Exception as e:
        return f"Error retrieving scores: {str(e)}"

@tool
def get_student_attendance(student_id: str) -> str:
    """Use this tool to fetch the current attendance percentage for a specific student_id."""
    try:
        records = get_tab("attendance").get_all_records()
        student_records = [r for r in records if str(r.get("student_id", "")) == student_id]
        if not student_records:
            return f"No attendance record found for {student_id}."
        
        output = [f"- Week of {r['week_of']}: {r['attendance_pct']}% ({r['classes_attended']}/{r['classes_scheduled']} classes)" for r in student_records]
        return "\n".join(output)
    except Exception as e:
        return f"Error retrieving attendance: {str(e)}"

@tool
def get_upcoming_exams(student_id: str) -> str:
    """Use this tool to fetch any upcoming exam dates and subjects for a specific student_id."""
    try:
        records = get_tab("exam_schedule").get_all_records()
        student_records = [r for r in records if str(r.get("student_id", "")) == student_id]
        if not student_records:
            return f"No upcoming exams found for {student_id}."
        
        output = [f"- {r['subject']} ({r['exam_type']}) on {r['exam_date']}" for r in student_records]
        return "\n".join(output)
    except Exception as e:
        return f"Error retrieving exams: {str(e)}"

def append_signal(student_id: str, student_name: str, signal_output):
    """
    Appends a detected signal to the 'signal_sheet' worksheet.
    Expected columns: Timestamp, Student ID, Name, Concern, Severity, Urgency, Status
    """
    try:
        # FIX 1: Use your existing helper function to grab the tab!
        sheet = get_tab("signal_sheet")
        
        # Format current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Prepare the row exactly matching your column headers
        row = [
            student_id,               # A: student_id
            "Automated Alert",        # B: signal_type (We can hardcode this since the AI generated it)
            signal_output.severity,   # C: severity
            signal_output.urgency,    # D: urgency
            signal_output.concern,    # E: reason
            timestamp,                # F: timestamp
            "Open"                    # G: actioned
        ]
        
        # Push to Google Sheets
        sheet.append_row(row)
        return True
        
    except Exception as e:
        print(f"DEBUG: Failed to append signal to Google Sheets: {e}")
        return False

def get_open_signals():
    """
    Fetches all student signals from the 'signal_sheet' worksheet
    where the actioned status is 'Open' or 'Deferred'.
    Returns a list of dictionaries representing the rows.
    """
    try:
        # Use your existing helper to open the correct tab
        sheet = get_tab("signal_sheet")
        all_records = sheet.get_all_records()
        
        # Filter for rows that haven't been finalized yet ("Open" or "Deferred")
        active_signals = []
        for record in all_records:
            status = str(record.get("actioned", "")).strip().lower()
            if status in ["open", "deferred"]:
                active_signals.append(record)
                
        return active_signals
        
    except Exception as e:
        print(f"DEBUG: Failed to fetch open signals: {e}")
        return []
def update_signal_status(student_id: str, timestamp: str, new_status: str):
    """
    Finds the exact signal in the Google Sheet and updates its 'actioned' status.
    """
    try:
        sheet = get_tab("signal_sheet")
        records = sheet.get_all_records()
        
        for idx, row in enumerate(records):
            # Match the exact signal using student_id and timestamp
            if str(row.get("student_id")) == student_id and str(row.get("timestamp")) == timestamp:
                # gspread rows are 1-indexed, and row 1 is headers. So we add 2.
                # 'actioned' is the 6th column
                sheet.update_cell(idx + 2, 7, new_status)
                return True
    except Exception as e:
        print(f"DEBUG: Failed to update signal status: {e}")
        return False