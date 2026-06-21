import streamlit as st
from datetime import datetime, time, date, timedelta
from tools.sheets_client import get_open_signals, update_signal_status
from tools.daily_planner import generate_schedule
from tools.calendar_client import create_calendar_event

def render_coach_view():
    st.title("👩‍💼 Coach Dashboard")
    st.markdown("### Daily Schedule Planner")

    # 1. Fetch the current queue
    with st.spinner("Checking student queue..."):
        signals = get_open_signals()
    
    if not signals:
        st.success("No students are currently in the queue. Enjoy your day!")
        return
        
    st.info(f"You have **{len(signals)}** students waiting for a session (Open/Deferred).")

    # 2. Coach Availability Inputs
    st.markdown("#### Set Your Availability Today")
    col1, col2 = st.columns(2)
    
    # Generate all possible 30-minute blocks in a 24-hour day
    all_times = [time(h, m) for h in range(24) for m in (0, 30)]
    
    with col1:
        # Start time defaults to 09:00 (index 18 in the list)
        default_start_index = 18 if len(all_times) > 18 else 0
        start_time = st.selectbox(
            "Start Time", 
            all_times, 
            index=default_start_index,
            format_func=lambda t: t.strftime('%H:%M')
        )
        
    with col2:
        # Dynamically filter end times to ONLY show times AFTER the selected start_time
        valid_end_times = [t for t in all_times if t > start_time]
        
        # If it's 23:30, there is no "later" time in the same day, so handle the edge case
        if not valid_end_times:
            st.error("No valid end times available for today.")
            end_time = start_time
        else:
            end_time = st.selectbox(
                "End Time", 
                valid_end_times, 
                format_func=lambda t: t.strftime('%H:%M')
            )

    # 3. Calculate Available Slots 
    # (We no longer need strict validation errors because the UI prevents them!)
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

    # 4. Generate AI Plan
    if st.button("🧠 Generate Daily Plan", type="primary"):
        with st.spinner("AI is building your optimized schedule..."):
            plan = generate_schedule(signals, total_slots)
            st.session_state.daily_plan = plan
            st.session_state.active_signals = signals

    # 5. Display the Plan and "Accept" Button
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
                
                current_slot_start = slot_end # Advance the clock 30 mins
                    
        st.markdown("---")
        st.subheader("⏭️ Deferred to Tomorrow")
        if not plan.deferred:
            st.success("No students were deferred!")
        else:
            for session in plan.deferred:
                st.warning(f"**{session.student_id}** - *Reason:* {session.reason}")

        # 6. The Final Execution Hook
        if st.button("✅ Accept & Sync to Calendar", type="primary"):
            with st.spinner("Syncing with Google Calendar and Sheets..."):
                current_slot_start = start_dt
                
                # Helper dictionary to quickly find the timestamp for a student
                student_to_timestamp = {s["student_id"]: s["timestamp"] for s in st.session_state.active_signals}

                # A. Process Scheduled Students
                for session in plan.scheduled:
                    slot_end = current_slot_start + timedelta(minutes=30)
                    
                    # 1. Create Calendar Event
                    create_calendar_event(
                        student_id=session.student_id,
                        session_type=session.session_type,
                        reason=session.reason,
                        start_dt=current_slot_start,
                        end_dt=slot_end
                    )
                    
                    # 2. Update Sheet to "Scheduled"
                    ts = student_to_timestamp.get(session.student_id, "")
                    update_signal_status(session.student_id, ts, "Scheduled")
                    
                    # Advance time
                    current_slot_start = slot_end
                    
                # B. Process Deferred Students
                for session in plan.deferred:
                    ts = student_to_timestamp.get(session.student_id, "")
                    update_signal_status(session.student_id, ts, "Deferred")

            # Clean up state and reload
            del st.session_state.daily_plan
            del st.session_state.active_signals
            st.success("All set! Calendar updated and queue refreshed.")
            st.rerun()