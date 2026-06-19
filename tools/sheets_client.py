import os
import json
import gspread
from langchain_core.tools import tool

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