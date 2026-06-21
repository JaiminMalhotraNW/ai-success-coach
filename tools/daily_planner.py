import json
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 1. Define the Structured Output Schema
class ScheduledSession(BaseModel):
    student_id: str = Field(description="The ID of the student.")
    reason: str = Field(description="Plain text reason for why they are scheduled today.")
    session_type: str = Field(description="E.g., 'Emergency Check-in', 'Academic Strategy', 'Stress Management'.")

class DeferredSession(BaseModel):
    student_id: str = Field(description="The ID of the student.")
    reason: str = Field(description="Valid reason for deferring them to tomorrow (e.g., lower urgency, lack of available slots).")

class DailyPlan(BaseModel):
    scheduled: list[ScheduledSession] = Field(default=[], description="List of students scheduled for today. MUST NOT exceed available slots.")
    deferred: list[DeferredSession] = Field(default=[], description="List of students deferred to tomorrow.")

# 2. The Planning Logic
def generate_schedule(signals: list, available_slots: int) -> DailyPlan:
    """
    Takes a list of open signals and the number of available slots,
    and returns a structured DailyPlan using GPT.
    """
    if not signals:
        return DailyPlan(scheduled=[], deferred=[])

    # Convert the signals to a clean JSON string for the prompt
    signals_json = json.dumps(signals, indent=2)

    system_prompt = f"""You are an expert Success Coach AI Planner.
    Your job is to read a queue of students needing help and build a daily schedule.
    
    CRITICAL RULES:
    1. The coach has EXACTLY {available_slots} slots available today. 
    2. You CANNOT schedule more than {available_slots} students. If there are more students than slots, you MUST defer the lowest priority ones.
    3. If available slots are 0, you must defer ALL students.
    
    PRIORITY RUBRIC:
    - Top Priority: Urgency = "Today"
    - High Priority: Status = "Deferred" (Do not make a student wait multiple days if possible)
    - Medium Priority: Urgency = "Tomorrow"
    - Low Priority: Urgency = "This Week" or "Next Week"
    
    For scheduled students, provide a 'session_type' (e.g., Academic Strategy, Crisis Management) and a short 'reason'.
    For deferred students, provide a short 'reason' explaining why they were pushed to tomorrow (e.g., "Schedule full today, lower urgency issue").
    """

    llm = ChatOpenAI(model="gpt-5.4-mini-2026-03-17", temperature=0).with_structured_output(DailyPlan)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Here is the current queue of students:\n{signals_json}")
    ]

    try:
        result = llm.invoke(messages)
        
        # Failsafe: Ensure the LLM didn't hallucinate extra slots
        if len(result.scheduled) > available_slots:
            # Force defer the overflow if the LLM disobeys
            overflow = result.scheduled[available_slots:]
            result.scheduled = result.scheduled[:available_slots]
            for session in overflow:
                result.deferred.append(
                    DeferredSession(
                        student_id=session.student_id, 
                        reason="System override: Coach schedule reached maximum capacity."
                    )
                )
                
        return result
        
    except Exception as e:
        print(f"DEBUG: Planning generation failed: {e}")
        # Safe fallback: Defer everyone if the AI crashes
        fallback_deferred = [
            DeferredSession(student_id=s.get("student_id", "Unknown"), reason="System error during planning. Deferred safely.") 
            for s in signals
        ]
        return DailyPlan(scheduled=[], deferred=fallback_deferred)