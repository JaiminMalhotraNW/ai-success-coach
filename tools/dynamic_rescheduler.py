import json
from datetime import date
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from tools.sheets_client import get_daily_schedule, get_open_signals

# 1. Strict schema for the inner list items
class OverrideSession(BaseModel):
    date: str = Field(description="The date of the session")
    time_slot: str = Field(description="The time slot, e.g., '22:00 - 22:30'")
    student_id: str = Field(description="The ID of the student")
    session_type: str = Field(description="The type of session")
    reason: str = Field(description="Reason for the session")

# 2. Strict schema for the LLM Output
class ReschedulePlanSchema(BaseModel):
    is_conflict_detected: bool = Field(description="True if a new critical/urgent signal needs to override the current schedule.")
    tradeoff_required: bool = Field(description="True ONLY if there are more critical students than available slots, requiring human choice.")
    changes_summary: str = Field(description="A clean, concise summary of who is being moved and why.")
    proposed_overrides: list[OverrideSession] = Field(description="List of updated schedule objects. If tradeoff_required is True, this MUST be an empty list [].")

# 3. Standard Python class for the UI
class ReschedulePlan:
    def __init__(self, is_conflict_detected, tradeoff_required, changes_summary, proposed_overrides):
        self.is_conflict_detected = is_conflict_detected
        self.tradeoff_required = tradeoff_required
        self.changes_summary = changes_summary
        self.proposed_overrides = proposed_overrides

def evaluate_schedule_overrides() -> ReschedulePlan:
    """
    Analyzes today's locked schedule against new open signals to detect emergencies.
    """
    today_str = date.today().strftime("%Y-%m-%d")
    
    current_schedule = get_daily_schedule(today_str)
    open_signals = get_open_signals()
    scheduled_student_ids = [s["student_id"] for s in current_schedule]
    
    unscheduled_signals = [s for s in open_signals if s["student_id"] not in scheduled_student_ids]

    if not unscheduled_signals or not current_schedule:
        return ReschedulePlan(
            is_conflict_detected=False,
            tradeoff_required=False,
            changes_summary="No critical overrides needed.",
            proposed_overrides=[]
        )

    system_prompt = f"""You are an elite Success Coach AI Scheduler.
    Look at the CURRENT LOCKED SCHEDULE and the NEW UNSCHEDULED SIGNALS.
    
    RULES:
    1. If there are NO Critical/Today signals in the UNSCHEDULED SIGNALS, set is_conflict_detected = False.
    2. If there IS a Critical/Today signal, set is_conflict_detected = True.
    3. SWAPPING: Attempt to swap the new Critical student into the schedule by replacing a low-priority student. Fill the proposed_overrides list with the new layout.
    4. TRADEOFF REQUIRED: If the scheduled students are ALSO high priority/crisis, set tradeoff_required = True, and YOU MUST SET proposed_overrides = []. Do not guess. Let the human decide.
    
    CURRENT SCHEDULE:
    {json.dumps(current_schedule)}
    
    NEW UNSCHEDULED SIGNALS:
    {json.dumps(unscheduled_signals)}
    """

    llm = ChatOpenAI(model="gpt-5.4-mini-2026-03-17", temperature=0).with_structured_output(ReschedulePlanSchema)
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Evaluate the schedule for critical overrides.")
    ]
    
    try:
        plan_schema = llm.invoke(messages)
        
        # Convert strict objects back to dicts for the UI
        overrides_as_dicts = [override.model_dump() for override in plan_schema.proposed_overrides]
        
        return ReschedulePlan(
            is_conflict_detected=plan_schema.is_conflict_detected,
            tradeoff_required=plan_schema.tradeoff_required,
            changes_summary=plan_schema.changes_summary,
            proposed_overrides=overrides_as_dicts
        )
    except Exception as e:
        print(f"DEBUG: Reschedule evaluation failed: {e}")
        return ReschedulePlan(
            is_conflict_detected=False,
            tradeoff_required=False,
            changes_summary="Error evaluating schedule.",
            proposed_overrides=[]
        )