"""
Mentor + Student tracker app.
Run with: streamlit run app.py
"""

import streamlit as st
import os
from datetime import date, datetime
from dotenv import load_dotenv
from streamlit_option_menu import option_menu

load_dotenv()

# When deployed on Streamlit Community Cloud, credentials live in
# st.secrets (set via the app's Settings > Secrets panel) instead of a
# local .env file. This merges them into the environment so every
# os.getenv(...) call in the rest of the app works identically whether
# running locally or deployed — no other file needs to change.
try:
    for key, value in st.secrets.items():
        os.environ.setdefault(key, str(value))
except Exception:
    pass  # no secrets configured (normal for local development)

from mentors import get_all_mentors, get_mentor_by_name
from mentor_checkins import (
    submit_checkin,
    get_flagged_checkins,
    get_ai_flagged_checkins,
    get_latest_checkin_for_group,
    this_monday,
)
from ai_layer import check_for_concerns
from coordinator_agent import generate_weekly_summary
from students import get_all_group_names, get_nickname_map_for_group, get_students_map_for_group
from student_checkins import (
    submit_student_checkin,
    get_not_coming_this_week,
    get_checkins_for_group,
    compute_monthly_scorecard,
)
from wishlist_items import (
    add_wishlist_item,
    get_wishlist_items_for_student,
    get_wishlist_items_for_student_month,
    update_wishlist_item,
    delete_wishlist_item,
)
from calendar_events import get_upcoming_events, get_general_events, add_event
from rsvps import submit_rsvp, get_coming_count_for_event, get_rsvps_for_event

st.set_page_config(page_title="High School Girls Tracker", page_icon="🌙", layout="wide")

# ---------- CUSTOM STYLING ----------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3 {
        font-family: 'Fraunces', serif !important;
        font-weight: 600 !important;
        color: #2B2B2B;
    }

    /* Section labels within forms */
    .section-label {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #6B8F71;
        margin: 1.1rem 0 0.3rem 0;
    }
    .section-label:first-child {
        margin-top: 0;
    }

    /* Card containers (st.container(border=True)) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px !important;
        border: 1px solid #E4DCC9 !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 1px 3px rgba(43,43,43,0.05);
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        border: none;
    }
    .stButton > button[kind="primary"] {
        background-color: #6B8F71;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #587a5e;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E4DCC9;
        border-radius: 12px;
        padding: 0.8rem;
    }

    /* Signature divider */
    .crescent-divider {
        text-align: center;
        color: #C7B99C;
        font-size: 0.9rem;
        letter-spacing: 0.3em;
        margin: 0.5rem 0 1.5rem 0;
    }

    /* Orbiting sparkles around the title */
    .title-orbit-wrap {
        position: relative;
        display: inline-block;
    }
    .orbit-sparkle {
        position: absolute;
        top: 50%;
        left: 50%;
        width: 14px;
        height: 14px;
        margin: -7px 0 0 -7px;
        transform-origin: center;
        animation-name: orbit;
        animation-timing-function: linear;
        animation-iteration-count: infinite;
    }
    @keyframes orbit {
        from { transform: rotate(0deg) translateX(var(--orbit-radius)) rotate(0deg); }
        to   { transform: rotate(360deg) translateX(var(--orbit-radius)) rotate(-360deg); }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- HEADER ----------
def load_svg(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""

logo_svg = load_svg("assets/logo.svg")
mentor_avatar_svg = load_svg("assets/mentor_avatar.svg")
student_avatar_svg = load_svg("assets/student_avatar.svg")

st.markdown(
    f"""
    <div style="padding: 1.5rem 0 0.3rem 0; text-align:center;">
        <div class="title-orbit-wrap">
            <span class="orbit-sparkle" style="--orbit-radius:190px; animation-duration:9s; color:#C7A552; font-size:14px;">✦</span>
            <span class="orbit-sparkle" style="--orbit-radius:190px; animation-duration:9s; animation-delay:-3s; color:#D8A7A0; font-size:12px;">✦</span>
            <span class="orbit-sparkle" style="--orbit-radius:190px; animation-duration:9s; animation-delay:-6s; color:#6B8F71; font-size:16px;">✦</span>
            <h1 style="margin-bottom:0; font-size:2.4rem;">High School Girls Tracker</h1>
        </div>
        <p style="color:#8A8371; margin-top:0.3rem; font-size:1.05rem;">Weekly check-ins, at a glance.</p>
        <div style="width:170px; margin:1rem auto 0 auto;">{logo_svg}</div>
    </div>
    <div class="crescent-divider" style="text-align:center;">✦ ⁛ ✦</div>
    """,
    unsafe_allow_html=True,
)

selected = option_menu(
    menu_title=None,
    options=["Mentor Check-in", "Mentor Dashboard", "Student Check-in", "Wishlist", "Parent View", "Events Calendar", "Coordinator Dashboard"],
    icons=["mortarboard-fill", "person-lock", "backpack2-fill", "gift-fill", "heart-fill", "calendar3", "bar-chart-line-fill"],
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#FDEFEF"},
        "icon": {"color": "#6B8F71", "font-size": "16px"},
        "nav-link": {
            "font-family": "Inter, sans-serif",
            "font-weight": "500",
            "font-size": "15px",
            "color": "#2B2B2B",
            "text-align": "center",
            "margin": "0px",
            "padding": "12px 18px",
        },
        "nav-link-selected": {
            "background-color": "#6B8F71",
            "color": "#FFFFFF",
        },
    },
)

# ---------- MENTOR CHECK-IN ----------
if selected == "Mentor Check-in":
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.5rem;">
            <div style="width:44px;">{mentor_avatar_svg}</div>
            <h2 style="margin:0;">Weekly Mentor Check-in</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    mentors = get_all_mentors()
    if not mentors:
        st.warning("No mentors found. Add mentors in Airtable first.")
    else:
        mentor_names = {
            m["fields"].get("Name", f"Unnamed mentor ({m['id'][-4:]})"): m["id"]
            for m in mentors
        }
        selected_name = st.selectbox("Your name", list(mentor_names.keys()))
        mentor_id = mentor_names[selected_name]

        auth_key = f"mentor_authenticated_{mentor_id}"
        if not st.session_state.get(auth_key):
            entered_mentor_password = st.text_input(
                "Your password", type="password", key=f"mentor_pw_checkin_{mentor_id}"
            )
            if st.button("Unlock", key=f"mentor_unlock_checkin_{mentor_id}"):
                mentor_record = get_mentor_by_name(selected_name)
                stored_password = mentor_record["fields"].get("Password", "") if mentor_record else ""
                if mentor_record and stored_password and entered_mentor_password == stored_password:
                    st.session_state[auth_key] = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
            st.stop()

        with st.form("mentor_checkin_form"):
            st.markdown('<div class="section-label">Attendance</div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                week_of = st.date_input("Week of", value=date.today())
                students_expected = st.number_input("Students expected", min_value=0, step=1)
            with col2:
                food_confirmed = st.checkbox("Food confirmed")
                students_not_coming = st.text_input("Students not coming (comma-separated)")

            st.markdown('<div class="section-label">This week</div>', unsafe_allow_html=True)
            discussion_topic = st.text_input("Discussion topic")
            activity_name = st.text_input("Activity name")
            reasons = st.text_area("Absent students and reasons (if known)")

            st.markdown('<div class="section-label">Your check-in</div>', unsafe_allow_html=True)
            attended_coord_meeting = st.checkbox("I attended the coordinator meeting")
            checked_meeting_notes = st.checkbox("I reviewed the meeting notes and to-do list for this week")
            flagged_situation = st.text_area("Anything urgent to flag?")
            notes_to_coordinator = st.text_area("Notes to coordinator")

            submitted = st.form_submit_button("Submit check-in", type="primary")

            if submitted:
                ai_result = check_for_concerns(
                    notes_to_coordinator=notes_to_coordinator,
                    reasons=reasons,
                    discussion_topic=discussion_topic,
                    flagged_situation=flagged_situation,
                )
                submit_checkin(
                    mentor_record_id=mentor_id,
                    week_of=week_of.isoformat(),
                    food_confirmed=food_confirmed,
                    students_expected=int(students_expected),
                    students_not_coming=students_not_coming,
                    reasons=reasons,
                    attended_coord_meeting=attended_coord_meeting,
                    notes_to_coordinator=notes_to_coordinator,
                    flagged_situation=flagged_situation,
                    checked_meeting_notes=checked_meeting_notes,
                    discussion_topic=discussion_topic,
                    activity_name=activity_name,
                    ai_flagged=ai_result["ai_flagged"],
                    ai_flag_reason=ai_result["ai_flag_reason"],
                )
                st.success("Check-in submitted.")

# ---------- MENTOR DASHBOARD (password-gated, own group only) ----------
elif selected == "Mentor Dashboard":
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.5rem;">
            <div style="width:44px;">{mentor_avatar_svg}</div>
            <h2 style="margin:0;">Mentor Dashboard</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("See your own students' weekly check-ins. Other mentors' groups aren't shown here.")

    mentors = get_all_mentors()
    if not mentors:
        st.warning("No mentors found. Add mentors in Airtable first.")
    else:
        mentor_names = [m["fields"].get("Name", f"Unnamed mentor ({m['id'][-4:]})") for m in mentors]
        dash_selected_name = st.selectbox("Your name", mentor_names, key="mentor_dashboard_name")

        mentor_record = get_mentor_by_name(dash_selected_name)
        mentor_id = mentor_record["id"] if mentor_record else None

        auth_key = f"mentor_authenticated_{mentor_id}"
        if not st.session_state.get(auth_key):
            entered_mentor_password = st.text_input(
                "Your password", type="password", key=f"mentor_pw_dash_{mentor_id}"
            )
            if st.button("Unlock", key=f"mentor_unlock_dash_{mentor_id}"):
                stored_password = mentor_record["fields"].get("Password", "") if mentor_record else ""
                if mentor_record and stored_password and entered_mentor_password == stored_password:
                    st.session_state[auth_key] = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
            st.stop()

        mentor_group = mentor_record["fields"].get("Group Name", "") if mentor_record else ""

        if not mentor_group:
            st.warning("No group is set for this mentor in Airtable yet — nothing to show.")
        else:
            st.markdown(f"**Group: {mentor_group}**")

            show_all_weeks = st.checkbox("Show all weeks (default: this week only)", key="mentor_dash_all_weeks")

            checkins = (
                get_checkins_for_group(mentor_group)
                if show_all_weeks
                else get_checkins_for_group(mentor_group, week_of=this_monday())
            )

            if not checkins:
                st.info("No check-ins found for your group yet.")
            else:
                for record in checkins:
                    f = record["fields"]
                    student_name = f.get("Name (from Student Name)", ["Unknown"])
                    student_name = student_name[0] if isinstance(student_name, list) else student_name

                    with st.container(border=True):
                        st.markdown(f"**{student_name}** — Week of {f.get('Week Of', '—')}")

                        coming = f.get("Coming This Week?", None)
                        if coming is False:
                            st.caption(f"Not coming — {f.get('The Reason Why (If not Coming)', 'no reason given')}")
                        elif coming is True:
                            st.caption("Coming this week")

                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"**Memorization goal:** {f.get('Memorization Goal', '—')}")
                            st.write(f"**Salah goal:** {f.get('Salah (Prayer) Goal', '—')}")
                        with col_b:
                            st.write(f"**Book pages read:** {f.get('Book Pages Read', 0)}")
                            st.write(f"**Quran pages:** {f.get('Quran Pages', 0)}")

                        if f.get("Activity Request"):
                            st.write(f"**Activity request:** {f.get('Activity Request')}")

# ---------- STUDENT CHECK-IN ----------
elif selected == "Student Check-in":
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.5rem;">
            <div style="width:44px;">{student_avatar_svg}</div>
            <h2 style="margin:0;">Weekly Student Check-in</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    group_names = get_all_group_names()
    if not group_names:
        st.warning("No students found. Add students in Airtable first.")
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            selected_group = st.selectbox("Your group", group_names)

        nickname_map = get_nickname_map_for_group(selected_group)

        if not nickname_map:
            st.info("No students with a nickname set yet in this group.")
        else:
            with col_b:
                selected_nickname = st.selectbox("Your nickname", list(nickname_map.keys()))

            students_map = get_students_map_for_group(selected_group)
            student_info = students_map.get(selected_nickname, {})
            student_record_id = student_info.get("id")
            student_pin = student_info.get("pin", "")

            if not student_pin:
                st.warning("No PIN has been set for you yet — ask your mentor or coordinator to add one in Airtable.")
                st.stop()

            pin_ok_key = f"student_pin_ok_{student_record_id}"
            if not st.session_state.get(pin_ok_key):
                entered_pin = st.text_input("Enter your PIN", type="password", key=f"pin_input_{student_record_id}")
                if st.button("Verify", key=f"pin_verify_{student_record_id}"):
                    if entered_pin == student_pin:
                        st.session_state[pin_ok_key] = True
                        # Reused by Events Calendar so a student doesn't need
                        # to identify themselves twice in the same session.
                        st.session_state["identified_student_id"] = student_record_id
                        st.rerun()
                    else:
                        st.error("Incorrect PIN.")
                st.stop()

            with st.form("student_checkin_form"):
                st.markdown('<div class="section-label">Attendance</div>', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    week_of = st.date_input("Week of", value=date.today(), key="student_week")
                    coming_this_week = st.checkbox("Coming this week", value=True)
                with col2:
                    reason_if_not_coming = st.text_input("If not coming, why?")

                st.markdown('<div class="section-label">Goals</div>', unsafe_allow_html=True)
                col_s, col_m = st.columns(2)
                with col_s:
                    salah_goal_met = st.checkbox("Did you meet your salah goal this week?")
                    salah_notes = st.text_area("Notes (optional)", key="salah_notes")
                with col_m:
                    memorization_goal_met = st.checkbox("Did you meet your memorization goal this week?")
                    memorization_notes = st.text_area("Notes (optional)", key="memorization_notes")

                st.markdown('<div class="section-label">Reading</div>', unsafe_allow_html=True)
                col3, col4 = st.columns(2)
                with col3:
                    book_pages_read = st.number_input("Book pages read", min_value=0, step=1)
                with col4:
                    pages_read = st.number_input("Quran pages read", min_value=0, step=1)

                st.markdown('<div class="section-label">Looking ahead</div>', unsafe_allow_html=True)
                activity_request = st.text_area("Activity request for upcoming weeks")

                submitted = st.form_submit_button("Submit check-in", type="primary")

                if submitted:
                    submit_student_checkin(
                        student_record_id=student_record_id,
                        week_of=week_of.isoformat(),
                        coming_this_week=coming_this_week,
                        reason_if_not_coming=reason_if_not_coming,
                        salah_goal_met=salah_goal_met,
                        salah_notes=salah_notes,
                        memorization_goal_met=memorization_goal_met,
                        memorization_notes=memorization_notes,
                        book_pages_read=int(book_pages_read),
                        pages_read=int(pages_read),
                        activity_request=activity_request,
                    )
                    st.success("Check-in submitted.")

# ---------- WISHLIST ----------
elif selected == "Wishlist":
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.5rem;">
            <div style="width:44px;">{student_avatar_svg}</div>
            <h2 style="margin:0;">Your Wishlist</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Reuse identification if already unlocked elsewhere this session
    # (Student Check-in or Events Calendar); otherwise ask here.
    student_record_id = st.session_state.get("identified_student_id")

    if not student_record_id:
        wl_group_names = get_all_group_names()
        if not wl_group_names:
            st.warning("No students found. Add students in Airtable first.")
            st.stop()

        col_a, col_b = st.columns(2)
        with col_a:
            wl_group = st.selectbox("Your group", wl_group_names, key="wishlist_group")

        wl_students_map = get_students_map_for_group(wl_group)
        if not wl_students_map:
            st.info("No students with a nickname set yet in this group.")
            st.stop()

        with col_b:
            wl_nickname = st.selectbox("Your nickname", list(wl_students_map.keys()), key="wishlist_nickname")

        wl_info = wl_students_map.get(wl_nickname, {})
        wl_candidate_id = wl_info.get("id")
        wl_stored_pin = wl_info.get("pin", "")

        if not wl_stored_pin:
            st.warning("No PIN has been set for you yet — ask your mentor or coordinator to add one in Airtable.")
            st.stop()

        pin_ok_key = f"student_pin_ok_{wl_candidate_id}"
        if not st.session_state.get(pin_ok_key):
            wl_entered_pin = st.text_input("Your PIN", type="password", key=f"wishlist_pin_{wl_candidate_id}")
            if st.button("Verify", key=f"wishlist_pin_verify_{wl_candidate_id}"):
                if wl_entered_pin == wl_stored_pin:
                    st.session_state[pin_ok_key] = True
                    st.session_state["identified_student_id"] = wl_candidate_id
                    st.rerun()
                else:
                    st.error("Incorrect PIN.")
            st.stop()

        student_record_id = wl_candidate_id

    # ---------- Add a new item ----------
    st.markdown('<div class="section-label">Add an item</div>', unsafe_allow_html=True)
    with st.form("add_wishlist_form", clear_on_submit=True):
        new_item_link = st.text_input("Amazon link")
        new_item_price = st.number_input("Price ($)", min_value=0.0, step=0.5, format="%.2f")
        add_submitted = st.form_submit_button("Add to wishlist", type="primary")

        if add_submitted:
            if not new_item_link:
                st.error("Please add a link before submitting.")
            else:
                add_wishlist_item(
                    student_record_id=student_record_id,
                    item_link=new_item_link,
                    item_price=float(new_item_price),
                    week_added=date.today().isoformat(),
                )
                st.success("Added to your wishlist.")
                st.rerun()

    # ---------- History: view / edit / delete ----------
    st.markdown('<div class="section-label">Your items</div>', unsafe_allow_html=True)
    all_items = get_wishlist_items_for_student(student_record_id)

    if not all_items:
        st.info("Nothing on your wishlist yet — add something above.")
    else:
        for item in all_items:
            f = item["fields"]
            with st.container(border=True):
                col_info, col_actions = st.columns([3, 1])
                with col_info:
                    st.markdown(f"[{f.get('Item Link', 'Untitled item')}]({f.get('Item Link', '#')})")
                    st.caption(f"${f.get('Item Price', 0):.2f} · added {f.get('Week Added', '—')}")
                    if f.get("Selected For Reward"):
                        st.success("✓ Selected for this month's reward")
                with col_actions:
                    with st.expander("Edit"):
                        edited_link = st.text_input(
                            "Link", value=f.get("Item Link", ""), key=f"edit_link_{item['id']}"
                        )
                        edited_price = st.number_input(
                            "Price ($)",
                            value=float(f.get("Item Price", 0)),
                            min_value=0.0,
                            step=0.5,
                            format="%.2f",
                            key=f"edit_price_{item['id']}",
                        )
                        col_save, col_delete = st.columns(2)
                        with col_save:
                            if st.button("Save", key=f"save_{item['id']}"):
                                update_wishlist_item(
                                    item["id"], {"Item Link": edited_link, "Item Price": edited_price}
                                )
                                st.rerun()
                        with col_delete:
                            if st.button("Delete", key=f"delete_{item['id']}"):
                                delete_wishlist_item(item["id"])
                                st.rerun()

    # ---------- This month's reward selection ----------
    st.divider()
    st.markdown('<div class="section-label">This month\'s reward</div>', unsafe_allow_html=True)

    today = date.today()
    scorecard = compute_monthly_scorecard(student_record_id, today.year, today.month)
    tier = scorecard["tier"]
    tier_caps = {"full": 30, "partial": 15, "none": 0}
    tier_labels = {"full": "Full reward", "partial": "Partial reward", "none": "No reward yet"}
    cap = tier_caps[tier]

    st.metric("Goal progress this month", f"{scorecard['percentage']}%")
    st.write(f"**{tier_labels[tier]}** — up to **${cap}** this month")

    if cap == 0:
        st.info("Keep working on your goals — you'll unlock a reward once you hit 60% or more.")
    else:
        month_items = get_wishlist_items_for_student_month(student_record_id, today.year, today.month)
        if not month_items:
            st.info("Add items above, then come back here to pick up to your reward amount.")
        else:
            st.caption(f"Select items totaling up to ${cap}:")
            running_total = 0.0
            chosen_ids = []
            for item in month_items:
                f = item["fields"]
                price = float(f.get("Item Price", 0))
                already_selected = bool(f.get("Selected For Reward"))
                would_exceed = (running_total + price) > cap
                disabled = would_exceed and not already_selected
                checked = st.checkbox(
                    f"{f.get('Item Link', 'Untitled item')} — ${price:.2f}",
                    value=already_selected,
                    disabled=disabled,
                    key=f"reward_select_{item['id']}",
                )
                if checked:
                    running_total += price
                    chosen_ids.append(item["id"])

            st.caption(f"Total selected: ${running_total:.2f} / ${cap}")

            if st.button("Confirm my selection", type="primary"):
                for item in month_items:
                    update_wishlist_item(
                        item["id"], {"Selected For Reward": item["id"] in chosen_ids}
                    )
                st.success("Saved — your coordinator will follow up to get these to you.")
                st.rerun()

# ---------- PARENT VIEW ----------
elif selected == "Parent View":
    if "parent_authenticated" not in st.session_state:
        st.session_state.parent_authenticated = False

    if not st.session_state.parent_authenticated:
        st.subheader("Parent Access")
        entered_parent_password = st.text_input("Enter parent password", type="password", key="parent_pw")
        if st.button("Unlock", key="parent_unlock"):
            if entered_parent_password == os.getenv("PARENT_PASSWORD"):
                st.session_state.parent_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.stop()

    st.markdown(
        """
        <div style="margin-bottom:0.5rem;">
            <h2 style="margin:0;">This Week's Sohbet &amp; Activity</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("This week's discussion topic and activity for your daughter's group.")

    group_names = get_all_group_names()
    if not group_names:
        st.warning("No groups found yet.")
    else:
        selected_group = st.selectbox("Your daughter's group", group_names, key="parent_group_select")

        checkin = get_latest_checkin_for_group(selected_group)

        if not checkin:
            st.info("No check-in has been submitted for this group yet.")
        else:
            f = checkin["fields"]
            with st.container(border=True):
                st.markdown(f"**Week of {f.get('Week Of', '—')}**")
                st.markdown("##### This week's sohbet")
                st.write(f.get("Discussion Topic of the Week", "Not recorded yet."))
                st.markdown("##### This week's activity")
                st.write(f.get("Activity Name of the Week", "Not recorded yet."))

# ---------- ACADEMIC CALENDAR ----------
elif selected == "Events Calendar":
    if not (
        st.session_state.get("parent_authenticated")
        or st.session_state.get("coordinator_authenticated")
        or st.session_state.get("identified_student_id")
    ):
        st.subheader("Access")
        who = st.radio("I am a:", ["Parent", "Student"], key="events_who", horizontal=True)

        if who == "Parent":
            entered_events_password = st.text_input("Enter parent password", type="password", key="events_pw")
            if st.button("Unlock", key="events_unlock_parent"):
                if entered_events_password == os.getenv("PARENT_PASSWORD"):
                    st.session_state.parent_authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        else:
            ev_group_names = get_all_group_names()
            if not ev_group_names:
                st.warning("No groups found yet.")
            else:
                ev_group = st.selectbox("Your group", ev_group_names, key="events_student_group")
                ev_students_map = get_students_map_for_group(ev_group)
                if not ev_students_map:
                    st.info("No students with a nickname set yet in this group.")
                else:
                    ev_nickname = st.selectbox(
                        "Your nickname", list(ev_students_map.keys()), key="events_student_nickname"
                    )
                    ev_pin = st.text_input("Your PIN", type="password", key="events_student_pin")
                    if st.button("Unlock", key="events_unlock_student"):
                        ev_info = ev_students_map.get(ev_nickname, {})
                        ev_stored_pin = ev_info.get("pin", "")
                        if ev_stored_pin and ev_pin == ev_stored_pin:
                            st.session_state["identified_student_id"] = ev_info.get("id")
                            st.rerun()
                        else:
                            st.error("Incorrect PIN.")
        st.stop()

    st.subheader("Events Calendar")
    st.caption("General program events.")

    # If a student is signed in (either just now, or already identified via
    # Student Check-in this session), we know exactly who to check RSVP
    # status for. Parents/coordinator get an optional picker instead, since
    # they aren't tied to one specific student.
    identified_student_id = st.session_state.get("identified_student_id")
    if not identified_student_id:
        with st.expander("Check a student's RSVP status (optional)"):
            id_group_names = get_all_group_names()
            id_options = {}
            for g in id_group_names:
                for nickname, sid in get_nickname_map_for_group(g).items():
                    id_options[f"{nickname} ({g})"] = sid
            if id_options:
                id_label = st.selectbox(
                    "Student", ["—"] + list(id_options.keys()), key="events_identify_select_optional"
                )
                if id_label != "—":
                    identified_student_id = id_options[id_label]

    general_events = get_general_events()

    if general_events:
        for record in general_events:
            f = record["fields"]
            event_date_str = f.get("Date", "")
            event_time_str = f.get("Time", "")
            event_location_str = f.get("Location", "")

            display_date = event_date_str
            try:
                parsed = datetime.fromisoformat(event_date_str)
                display_date = parsed.strftime("%b %d, %Y")
            except (ValueError, AttributeError):
                pass

            with st.container(border=True):
                col_date, col_info = st.columns([1, 3])
                with col_date:
                    st.markdown(f"**{display_date}**")
                    if event_time_str:
                        st.caption(event_time_str)
                    if event_location_str:
                        st.caption(event_location_str)
                with col_info:
                    st.markdown(f"**{f.get('Event Name', 'Untitled event')}**")
                    if f.get("Description"):
                        st.write(f.get("Description"))

                    if st.session_state.get("coordinator_authenticated"):
                        coming_count = get_coming_count_for_event(record["id"])
                        st.caption(f"{coming_count} coming so far")

                    if identified_student_id:
                        rsvps_this_event = get_rsvps_for_event(record["id"])
                        already_going = any(
                            r["fields"].get("Coming")
                            and identified_student_id in r["fields"].get("Student Name", [])
                            for r in rsvps_this_event
                        )
                        if already_going:
                            st.success("✓ You're signed up for this event.")
                        else:
                            st.caption("Not signed up for this event yet.")

                    with st.expander("RSVP to this event"):
                        success_key = f"rsvp_success_{record['id']}"
                        if st.session_state.get(success_key):
                            st.success(st.session_state[success_key])
                            del st.session_state[success_key]

                        rsvp_group_names = get_all_group_names()
                        if not rsvp_group_names:
                            st.info("No students found yet.")
                        else:
                            rsvp_group = st.selectbox(
                                "Your group", rsvp_group_names, key=f"rsvp_group_{record['id']}"
                            )
                            rsvp_nickname_map = get_nickname_map_for_group(rsvp_group)

                            if not rsvp_nickname_map:
                                st.info("No students with a nickname set yet in this group.")
                            else:
                                rsvp_nickname = st.selectbox(
                                    "Your nickname",
                                    list(rsvp_nickname_map.keys()),
                                    key=f"rsvp_nickname_{record['id']}",
                                )
                                if st.button("I'm coming", key=f"rsvp_button_{record['id']}"):
                                    submit_rsvp(
                                        event_record_id=record["id"],
                                        student_record_id=rsvp_nickname_map[rsvp_nickname],
                                        coming=True,
                                    )
                                    st.session_state[success_key] = f"Successfully registered for the event, {rsvp_nickname}."
                                    st.rerun()
    else:
        st.info("No events yet.")

    st.divider()

    with st.expander("Add a new event (coordinator only)"):
        if st.session_state.get("coordinator_authenticated"):
            with st.form("add_event_form"):
                new_event_name = st.text_input("Event name")
                col_d, col_t = st.columns(2)
                with col_d:
                    new_event_date = st.date_input("Date", value=date.today())
                with col_t:
                    new_event_time = st.time_input("Time")
                new_event_description = st.text_area("Description (optional)")

                add_submitted = st.form_submit_button("Add event", type="primary")

                if add_submitted:
                    add_event(
                        event_name=new_event_name,
                        event_date=new_event_date.isoformat(),
                        event_time=new_event_time.strftime("%I:%M %p"),
                        group_name="",  # general calendar only for now
                        description=new_event_description,
                    )
                    st.success("Event added.")
                    st.rerun()
        else:
            add_password = st.text_input("Enter coordinator password to add events", type="password", key="calendar_pw")
            if st.button("Unlock", key="calendar_unlock"):
                if add_password == os.getenv("COORDINATOR_PASSWORD"):
                    st.session_state.coordinator_authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")

# ---------- COORDINATOR DASHBOARD ----------
elif selected == "Coordinator Dashboard":
    if "coordinator_authenticated" not in st.session_state:
        st.session_state.coordinator_authenticated = False

    if not st.session_state.coordinator_authenticated:
        st.subheader("Coordinator Access")
        entered_password = st.text_input("Enter coordinator password", type="password")
        if st.button("Unlock"):
            if entered_password == os.getenv("COORDINATOR_PASSWORD"):
                st.session_state.coordinator_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.stop()

    coordinator_name = os.getenv("COORDINATOR_NAME", "Coordinator")
    st.subheader(f"Welcome back, {coordinator_name}")

    with st.container(border=True):
        st.markdown("#### This week, at a glance")

        if st.button("Generate weekly summary", type="primary"):
            with st.spinner("Reading through this week's check-ins..."):
                summary = generate_weekly_summary(this_monday())
                st.session_state["weekly_summary"] = summary

        if "weekly_summary" in st.session_state:
            st.markdown(st.session_state["weekly_summary"])

    st.divider()

    st.subheader("Coordinator Dashboard")

    flagged = get_flagged_checkins()
    ai_flagged = get_ai_flagged_checkins()
    not_coming = get_not_coming_this_week(this_monday())
    events = get_upcoming_events(this_monday())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Flagged situations", len(flagged))
    col2.metric("AI-detected concerns", len(ai_flagged))
    col3.metric("Not coming this week", len(not_coming))
    col4.metric("Upcoming events", len(events))

    st.divider()

    left, right = st.columns(2)

    with left:
        st.markdown("### Flagged mentor situations")
        st.caption("Manually flagged by the mentor.")
        if flagged:
            for record in flagged:
                f = record["fields"]
                with st.container(border=True):
                    st.markdown(f"**Week of {f.get('Week Of')}**")
                    st.write(f.get("Flagged Situation", "No details"))
        else:
            st.info("Nothing flagged right now.")

        st.markdown("### AI-detected concerns")
        st.caption("Automatically surfaced from check-in notes — review and confirm.")
        if ai_flagged:
            for record in ai_flagged:
                f = record["fields"]
                with st.container(border=True):
                    st.markdown(f"**Week of {f.get('Week Of')}**")
                    st.write(f.get("AI Flag Reason", "No details"))
        else:
            st.info("No AI-detected concerns right now.")

        st.markdown("### Students not coming")
        st.caption("Shown with real names, since this view is for you as coordinator.")
        if not_coming:
            for record in not_coming:
                f = record["fields"]
                name = f.get("Name (from Student Name)", ["Unknown"])
                name = name[0] if isinstance(name, list) else name
                reason = f.get("The Reason Why (If not Coming)", "No reason given")
                with st.container(border=True):
                    st.markdown(f"**{name}**")
                    st.write(reason)
        else:
            st.info("Everyone's coming (or no submissions yet).")

    with right:
        st.markdown("### Upcoming events")
        if events:
            for record in events:
                f = record["fields"]
                with st.container(border=True):
                    st.markdown(f"**{f.get('Event Name')}**")
                    st.caption(f"{f.get('Date')} · {f.get('Group Name') or 'All groups'}")

                    rsvps = get_rsvps_for_event(record["id"])
                    coming_names = []
                    for r in rsvps:
                        if r["fields"].get("Coming"):
                            name = r["fields"].get("Name (from Student Name)", ["Unknown"])
                            name = name[0] if isinstance(name, list) else name
                            coming_names.append(name)

                    if coming_names:
                        st.markdown(f"**Coming ({len(coming_names)}):**")
                        st.write(", ".join(coming_names))
                    else:
                        st.caption("No RSVPs yet.")
        else:
            st.info("No upcoming events found.")