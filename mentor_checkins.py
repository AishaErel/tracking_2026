"""
Functions specific to the WeeklyCheckins table.

Note: the "Mentor" field is a Link to another record, so Airtable expects
a LIST of record IDs, e.g. ["recXXXXXXXX"], even though it's just one mentor.
"""

import os
from datetime import date, datetime, timedelta
from airtable_client import list_records, create_record

TABLE_NAME = os.getenv("AIRTABLE_CHECKINS_TABLE", "WeeklyCheckins")


def submit_checkin(
    mentor_record_id: str,
    week_of: str,                 # "YYYY-MM-DD"
    food_confirmed: bool,
    students_expected: int,
    students_not_coming: str,     # free text, e.g. "John, Maria"
    reasons: str,
    attended_coord_meeting: bool,
    notes_to_coordinator: str,
    flagged_situation: str,
    discussion_topic: str,
    activity_name: str,
    checked_meeting_notes: bool,
    ai_flagged: bool = False,
    ai_flag_reason: str = "",
) -> dict:
    fields = {
        "Mentor": [mentor_record_id],
        "Week Of": week_of,
        "Discussion Topic of the Week": discussion_topic,
        "Activity Name of the Week": activity_name,
        "Food Confirmed": food_confirmed,
        "Students Expected": students_expected,
        "Students Not Coming": students_not_coming,
        "Reasons": reasons,
        "Attended Coord Meeting": attended_coord_meeting,
        "Checked Meeting Notes": checked_meeting_notes,
        "Notes To Coordinator": notes_to_coordinator,
        "Flagged Situation": flagged_situation,
        "AI Flagged": ai_flagged,
        "AI Flag Reason": ai_flag_reason,
    }
    return create_record(TABLE_NAME, fields)


def get_checkins_for_week(week_of: str) -> list[dict]:
    """
    All check-ins submitted during the week starting on week_of (a Monday).

    Uses a date RANGE rather than exact equality, because a mentor's "Week of"
    date picker defaults to today's actual date — which only equals the
    computed Monday if they happen to submit on a Monday. Matching the whole
    week avoids silently missing valid submissions.
    """
    start = datetime.fromisoformat(week_of).date()
    end = start + timedelta(days=7)
    formula = (
        f"AND(IS_ON_OR_AFTER({{Week Of}}, DATETIME_PARSE('{start.isoformat()}', 'YYYY-MM-DD')), "
        f"IS_BEFORE({{Week Of}}, DATETIME_PARSE('{end.isoformat()}', 'YYYY-MM-DD')))"
    )
    return list_records(TABLE_NAME, formula=formula)


def get_flagged_checkins() -> list[dict]:
    """
    Anything a mentor manually flagged as needing attention.
    'Flagged Situation' is a text field, so we check it's non-empty.
    """
    return list_records(TABLE_NAME, formula="NOT({Flagged Situation} = '')")


def get_ai_flagged_checkins() -> list[dict]:
    """Anything the AI safety-net layer flagged, independent of manual flags."""
    return list_records(TABLE_NAME, formula="{AI Flagged} = TRUE()")


def get_latest_checkin_for_group(group_name: str) -> dict | None:
    """
    Most recent check-in for a given group, used for the parent-facing view
    (discussion topic + activity only — no individual student data).
    Relies on a 'Group Name (from Mentor)' lookup field already on this table.
    """
    formula = f"{{Group Name (from Mentor)}} = '{group_name}'"
    records = list_records(TABLE_NAME, formula=formula)
    if not records:
        return None
    records_sorted = sorted(records, key=lambda r: r["fields"].get("Week Of", ""), reverse=True)
    return records_sorted[0]


def get_missing_checkins(all_mentor_record_ids: list[str], week_of: str) -> list[str]:
    """
    Returns mentor record IDs who have NOT submitted a check-in for the given week.
    Useful for your reminder logic.
    """
    submitted = get_checkins_for_week(week_of)
    submitted_mentor_ids = set()
    for record in submitted:
        linked = record["fields"].get("Mentor", [])
        submitted_mentor_ids.update(linked)

    return [mid for mid in all_mentor_record_ids if mid not in submitted_mentor_ids]


def this_monday() -> str:
    """Helper: returns this week's Monday as YYYY-MM-DD, a sane default for 'Week Of'."""
    today = date.today()
    monday = today.fromordinal(today.toordinal() - today.weekday())
    return monday.isoformat()
