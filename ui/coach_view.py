import streamlit as st
from collections import defaultdict
from datetime import datetime, time, date, timedelta

from tools.sheets_client import get_open_signals, update_signal_status, get_roster, clear_and_save_daily_schedule
from tools.daily_planner import generate_schedule
from tools.calendar_client import create_calendar_event
from tools.brief_generator import generate_student_brief
from tools.dynamic_rescheduler import evaluate_schedule_overrides

@st.cache_data(ttl=600)
def fetch_roster():
    return get_roster()

def render_coach_view():
    st.title("👩‍💼 Coach Dashboard")
    
    # ==========================================
    # --- M9: DYNAMIC EMERGENCY RESCHEDULER ---
    # ==========================================
    # We check if there are any new critical signals that conflict with today's locked schedule.
    today_str = date.today().strftime("%Y-%m-%d")
    
    with st.spinner("Checking system for active emergencies..."):
        reschedule_plan = evaluate_schedule_overrides()
        
    if reschedule_plan.is_conflict_detected:
        st.error("🚨 **Critical Updates Detected in the Queue!**")
        with st.container(border=True):
            st.markdown(f"**AI Assessment:** {reschedule_plan.changes_summary}")
            
            if reschedule_plan.tradeoff_required:
                st.warning("⚖️ **Tradeoff Required:** There are more critical emergencies than available slots. Please manually review the signals below and decide who takes priority.")
            else:
                st.info("The AI has proposed an automatic schedule swap to accommodate this emergency.")
                if st.button("✅ Approve Override & Update Schedule", type="primary"):
                    with st.spinner("Swapping schedule and updating calendar..."):
                        # 1. Update the Daily Schedule Master Tab
                        clear_and_save_daily_schedule(today_str, reschedule_plan.proposed_overrides)
                        
                        # 2. Update Calendar for the newly inserted student
                        # (In a full production app, we would also delete the old calendar event, 
                        # but for this scope, we just add the new critical one)
                        for session in reschedule_plan.proposed_overrides:
                            create_calendar_event(
                                student_id=session["student_id"],
                                session_type=session["session_type"],
                                reason=f"[EMERGENCY OVERRIDE] {session['reason']}",
                                start_dt=datetime.now(), # Defaulting to next available for simplicity
                                end_dt=datetime.now() + timedelta(minutes=30)
                            )
                        
                        st.success("Emergency Override Applied! Schedule and Calendar Updated.")
                        st.rerun()

    st.markdown("---")

    # ==========================================
    # --- M8: PRE-MEETING BRIEFS ---
    # ==========================================
    st.markdown("### 📝 Pre-Meeting Briefs")
    st.write("Generate an AI-powered summary before you step into a session.")
    
    roster = fetch_roster()
    if roster:
        options = {"": None}
        options.update({f"{r['student_id']} - {r['name']}": r for r in roster})
        
        selected_option = st.selectbox("Select a student to brief:", list(options.keys()))
        
        if selected_option and options[selected_option]:
            student_id = options[selected_option]["student_id"]
            student_name = options[selected_option]["name"]
            
            if st.button("🧠 Generate Brief", type="primary"):
                with st.spinner(f"Compiling 360° brief for {student_name}..."):
                    brief = generate_student_brief(student_id, student_name)
                    
                    st.success("Brief Generated!")
                    with st.container(border=True):
                        st.subheader(f"Brief: {student_name}")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**🎓 Academic Overview**")
                            st.info(brief.academic_overview)
                            
                            st.markdown("**⏳ Historical Shifts**")
                            st.info(brief.historical_shifts)
                            
                        with col2:
                            st.markdown("**🚨 Open Concerns**")
                            st.warning(brief.open_concerns)
                            
                            st.markdown("**🗣️ Conversation Starters**")
                            for starter in brief.conversation_starters:
                                st.markdown(f"- {starter}")

    st.markdown("---")

    # ==========================================
    # --- M7: DAILY SCHEDULE PLANNER ---
    # ==========================================
    st.markdown("### 📅 Daily Schedule Planner")

    with st.spinner("Checking student queue..."):
        signals = get_open_signals()
    
    if not signals:
        st.success("No students are currently in the queue. Enjoy your day!")
        return
        
    st.info(f"You have **{len(signals)}** students waiting for a session (Open/Deferred).")

    st.markdown("#### Set Your Availability Today")
    col1, col2 = st.columns(2)
    
    all_times = [time(h, m) for h in range(24) for m in (0, 30)]
    
    with col1:
        default_start_index = 18 if len(all_times) > 18 else 0
        start_time = st.selectbox("Start Time", all_times, index=default_start_index, format_func=lambda t: t.strftime('%H:%M'))
        
    with col2:
        valid_end_times = [t for t in all_times if t > start_time]
        if not valid_end_times:
            st.error("No valid end times available for today.")
            end_time = start_time
        else:
            end_time = st.selectbox("End Time", valid_end_times, format_func=lambda t: t.strftime('%H:%M'))

    start_dt = datetime.combine(date.today(), start_time)
    end_dt = datetime.combine(date.today(), end_time)
    
    if start_dt < datetime.now():
         st.warning("⏳ Note: The selected Start Time has already passed today.")

    if end_time > start_time:
        duration_minutes = (end_dt - start_dt).total_seconds() / 60
        total_slots = int(duration_minutes // 30)
        st.success(f"You have time for **{total_slots}** sessions (30 mins each) today.")
    else:
        total_slots = 0

    if st.button("🧠 Generate Daily Plan"):
        with st.spinner("AI is building your optimized schedule..."):
            plan = generate_schedule(signals, total_slots)
            st.session_state.daily_plan = plan
            st.session_state.active_signals = signals

    if "daily_plan" in st.session_state:
        plan = st.session_state.daily_plan
        
        st.markdown("---")
        st.subheader("Proposed Schedule")
        
        if not plan.scheduled:
            st.info("No students scheduled for today.")
        else:
            current_slot_start = start_dt
            for idx, session in enumerate(plan.scheduled):
                slot_end = current_slot_start + timedelta(minutes=30)
                time_str = f"{current_slot_start.strftime('%I:%M %p')} - {slot_end.strftime('%I:%M %p')}"
                with st.expander(f"Slot {idx + 1} ({time_str}): {session.student_id} - {session.session_type}", expanded=True):
                    st.write(f"**Reason for scheduling:** {session.reason}")
                current_slot_start = slot_end 
                    
        st.markdown("---")
        st.subheader("⏭️ Deferred to Tomorrow")
        if not plan.deferred:
            st.success("No students were deferred!")
        else:
            for session in plan.deferred:
                st.warning(f"**{session.student_id}** - *Reason:* {session.reason}")

        if st.button("✅ Accept & Sync to Calendar", type="primary"):
            with st.spinner("Syncing with Google Calendar and Sheets..."):
                current_slot_start = start_dt
                
                # BUG FIX: Use defaultdict(list) to grab ALL timestamps for a student
                # so that if a student has 2 open signals, BOTH get closed!
                student_to_timestamps = defaultdict(list)
                for s in st.session_state.active_signals:
                    student_to_timestamps[s["student_id"]].append(s["timestamp"])

                schedule_to_save = []

                # Schedule Accepted Students
                for session in plan.scheduled:
                    slot_end = current_slot_start + timedelta(minutes=30)
                    time_str = f"{current_slot_start.strftime('%H:%M')} - {slot_end.strftime('%H:%M')}"
                    
                    # 1. Add to Google Calendar
                    create_calendar_event(
                        student_id=session.student_id,
                        session_type=session.session_type,
                        reason=session.reason,
                        start_dt=current_slot_start,
                        end_dt=slot_end
                    )
                    
                    # 2. Append to our Master Schedule List
                    schedule_to_save.append({
                        "date": today_str,
                        "time_slot": time_str,
                        "student_id": session.student_id,
                        "session_type": session.session_type,
                        "reason": session.reason
                    })
                    
                    # 3. Update ALL signals for this student to "Scheduled"
                    for ts in student_to_timestamps.get(session.student_id, []):
                        update_signal_status(session.student_id, ts, "Scheduled")
                    
                    current_slot_start = slot_end
                    
                # 4. Save the Master Schedule to the new tab!
                clear_and_save_daily_schedule(today_str, schedule_to_save)
                    
                # Update Deferred Students
                for session in plan.deferred:
                    for ts in student_to_timestamps.get(session.student_id, []):
                        update_signal_status(session.student_id, ts, "Deferred")

            del st.session_state.daily_plan
            del st.session_state.active_signals
            st.success("All set! Calendar and Master Schedule updated. Queue refreshed.")
            st.rerun()