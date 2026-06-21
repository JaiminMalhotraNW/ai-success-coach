import streamlit as st
from datetime import datetime, time, date, timedelta
from tools.sheets_client import get_open_signals, update_signal_status, get_roster
from tools.daily_planner import generate_schedule
from tools.calendar_client import create_calendar_event
from tools.brief_generator import generate_student_brief

@st.cache_data(ttl=600)
def fetch_roster():
    return get_roster()

def render_coach_view():
    st.title("👩‍💼 Coach Dashboard")
    
    # --- NEW: M8 PRE-MEETING BRIEFS ---
    st.markdown("### 📝 Pre-Meeting Briefs")
    st.write("Generate an AI-powered summary before you step into a session.")
    
    roster = fetch_roster()
    if roster:
        # Create a dropdown for all students
        options = {"": None}
        options.update({f"{r['student_id']} - {r['name']}": r for r in roster})
        
        selected_option = st.selectbox("Select a student to brief:", list(options.keys()))
        
        if selected_option and options[selected_option]:
            student_id = options[selected_option]["student_id"]
            student_name = options[selected_option]["name"]
            
            if st.button("🧠 Generate Brief", type="primary"):
                with st.spinner(f"Compiling 360° brief for {student_name} from Sheets, Signals, and Mem0..."):
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

    # --- M7 DAILY SCHEDULE PLANNER (Existing Code) ---
    st.markdown("### Daily Schedule Planner")

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
        start_time = st.selectbox(
            "Start Time", 
            all_times, 
            index=default_start_index,
            format_func=lambda t: t.strftime('%H:%M')
        )
        
    with col2:
        valid_end_times = [t for t in all_times if t > start_time]
        
        if not valid_end_times:
            st.error("No valid end times available for today.")
            end_time = start_time
        else:
            end_time = st.selectbox(
                "End Time", 
                valid_end_times, 
                format_func=lambda t: t.strftime('%H:%M')
            )

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
        st.subheader("📅 Proposed Schedule")
        
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
                
                student_to_timestamp = {s["student_id"]: s["timestamp"] for s in st.session_state.active_signals}

                for session in plan.scheduled:
                    slot_end = current_slot_start + timedelta(minutes=30)
                    
                    create_calendar_event(
                        student_id=session.student_id,
                        session_type=session.session_type,
                        reason=session.reason,
                        start_dt=current_slot_start,
                        end_dt=slot_end
                    )
                    
                    ts = student_to_timestamp.get(session.student_id, "")
                    update_signal_status(session.student_id, ts, "Scheduled")
                    
                    current_slot_start = slot_end
                    
                for session in plan.deferred:
                    ts = student_to_timestamp.get(session.student_id, "")
                    update_signal_status(session.student_id, ts, "Deferred")

            del st.session_state.daily_plan
            del st.session_state.active_signals
            st.success("All set! Calendar updated and queue refreshed.")
            st.rerun()