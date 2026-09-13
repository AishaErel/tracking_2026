"""
Functions specific to the StudentsCheckins table.

Note: "Student Name" is a Link to another record field, so it expects a LIST
of record IDs, e.g. ["recXXXXXXXX"].

"Name (from Student Name)" and "Group Name (from Student Name)" are Airtable
LOOKUP fields — they auto-populate from the linked Student record once
"Student Name" is set. Never write to them directly; they're read-only.

Scoring / reward system:
- Every student sets their own goals, so points are designed to measure
  "did you do what you said you'd do," not raw output — with one exception
  (Quran/book pages), which are left uncapped since reading pace varies a
  lot by age/level and shouldn't be judged against a shared bar.
- "Core" points (submission + attendance + salah + memorization) have a
  fixed weekly max of 58 for every student. Reward tier is based on
  % of a student's OWN monthly core max, not a shared point target.
- Quran/book pages are bonus points on top — they count toward total score
  shown to the student, but not toward the reward tier percentage.
"""

import os
import calendar
from datetime import date
from airtable_client import list_records, create_record

TABLE_NAME = os.getenv("AIRTABLE_STUDENT_CHECKINS_TABLE", "StudentsCheckins")

# ---------- Scoring constants ----------
POINTS_SUBMISSION = 15
POINTS_ATTENDANCE = 25
POINTS_MISSED_WEEK_PENALTY = -5
POINTS_SALAH_GOAL_MET = 10
POINTS_MEMORIZATION_GOAL_MET = 8
POINTS_PER_QURAN_PAGE = 3
POINTS_PER_BOOK_PAGE = 2
CORE_MAX_PER_WEEK = (
    POINTS_SUBMISSION + POINTS_ATTENDANCE + POINTS_SALAH_GOAL_MET + POINTS_MEMORIZATION_GOAL_MET
)  # 58

TIER_FULL_THRESHOLD = 90
TIER_PARTIAL_THRESHOLD = 60


def submit_student_checkin(
    student_record_id: str,
    week_of: str,                    # "YYYY-MM-DD"
    coming_this_week: bool,
    reason_if_not_coming: str,
    salah_goal_met: bool,
    salah_notes: str,
    memorization_goal_met: bool,
    memorization_notes: str,
    book_pages_read: int,
    pages_read: int,                 # Quran pages
    activity_request: str,
) -> dict:
    fields = {
        "Week Of": week_of,
        "Student Name": [student_record_id],
        "Coming This Week?": coming_this_week,
        "The Reason Why (If not Coming)": reason_if_not_coming,
        "Book Pages Read": book_pages_read,
        "Salah Goal Met": salah_goal_met,
        "Salah (Prayer) Goal": salah_notes,
        "Memorization Goal Met": memorization_goal_met,
        "Memorization Goal": memorization_notes,
        "Quran Pages": pages_read,
        "Activity Request": activity_request,
    }
    return create_record(TABLE_NAME, fields)


def get_checkins_for_week(week_of: str) -> list[dict]:
    return list_records(TABLE_NAME, formula=f"{{Week Of}} = '{week_of}'")


def get_not_coming_this_week(week_of: str) -> list[dict]:
    """Students who marked themselves as not coming, with their reason."""
    formula = f"AND({{Week Of}} = '{week_of}', {{Coming This Week?}} = FALSE())"
    return list_records(TABLE_NAME, formula=formula)


def get_checkins_for_group(group_name: str, week_of: str | None = None) -> list[dict]:
    """
    All student check-ins for a given group, used to scope the Mentor
    Dashboard to only that mentor's own students.

    Relies on 'Group Name (from Student Name)' — a lookup field already on
    this table — so a mentor never sees another group's check-ins.

    If week_of is given, results are limited to that exact week; otherwise
    all check-ins for the group are returned, most recent first.
    """
    if week_of:
        formula = (
            f"AND({{Group Name (from Student Name)}} = '{group_name}', "
            f"{{Week Of}} = '{week_of}')"
        )
    else:
        formula = f"{{Group Name (from Student Name)}} = '{group_name}'"

    records = list_records(TABLE_NAME, formula=formula)
    return sorted(records, key=lambda r: r["fields"].get("Week Of", ""), reverse=True)


def get_checkins_for_student_month(student_record_id: str, year: int, month: int) -> list[dict]:
    """
    All check-ins for one student within a calendar month, used for the
    monthly points/reward calculation. Filters by date range (not exact
    equality) since a student's 'Week Of' isn't guaranteed to fall exactly
    on a Monday.
    """
    start = date(year, month, 1).isoformat()
    last_day = calendar.monthrange(year, month)[1]
    end = date(year, month, last_day).isoformat()

    formula = (
        f"AND(IS_ON_OR_AFTER({{Week Of}}, DATETIME_PARSE('{start}', 'YYYY-MM-DD')), "
        f"IS_ON_OR_BEFORE({{Week Of}}, DATETIME_PARSE('{end}', 'YYYY-MM-DD')))"
    )
    all_recs = list_records(TABLE_NAME, formula=formula)
    return [r for r in all_recs if student_record_id in r["fields"].get("Student Name", [])]


def _count_mondays_in_month(year: int, month: int) -> int:
    """How many weeks (Mondays) fall in a given month — used as the basis
    for that student's monthly core-points max."""
    cal = calendar.Calendar()
    return sum(
        1 for day in cal.itermonthdates(year, month)
        if day.month == month and day.weekday() == 0
    )


def compute_monthly_scorecard(student_record_id: str, year: int, month: int) -> dict:
    """
    Computes one student's points and reward tier for a given month.

    Core points (submission + attendance + salah + memorization) are
    compared against that student's own monthly max — so tier is based on
    % of their own ceiling, not a number shared across all students.

    Quran/book pages are bonus points: included in total_points shown to
    the student, but excluded from the tier percentage since page counts
    vary naturally by age/reading level.

    A week with no check-in submitted at all still counts as a missed
    week and applies the same penalty as marking "not coming."
    """
    checkins = get_checkins_for_student_month(student_record_id, year, month)
    total_weeks = _count_mondays_in_month(year, month)

    weeks_seen = {}
    core_points = 0
    bonus_points = 0
    wishlist_links = []

    for r in checkins:
        f = r["fields"]
        week_key = f.get("Week Of")
        if week_key in weeks_seen:
            continue  # only count the first submission for a given week
        weeks_seen[week_key] = True

        pts = POINTS_SUBMISSION
        if f.get("Coming This Week?"):
            pts += POINTS_ATTENDANCE
        else:
            pts += POINTS_MISSED_WEEK_PENALTY
        if f.get("Salah Goal Met"):
            pts += POINTS_SALAH_GOAL_MET
        if f.get("Memorization Goal Met"):
            pts += POINTS_MEMORIZATION_GOAL_MET

        core_points += pts
        bonus_points += (
            f.get("Quran Pages", 0) * POINTS_PER_QURAN_PAGE
            + f.get("Book Pages Read", 0) * POINTS_PER_BOOK_PAGE
        )

        link = f.get("Wishlist Link This Week")
        if link:
            wishlist_links.append({"week": week_key, "link": link})

    weeks_missing = total_weeks - len(weeks_seen)
    core_points += weeks_missing * POINTS_MISSED_WEEK_PENALTY

    core_max = total_weeks * CORE_MAX_PER_WEEK
    percentage = round((core_points / core_max) * 100, 1) if core_max else 0.0

    if percentage >= TIER_FULL_THRESHOLD:
        tier = "full"        # 2 items, up to $30
    elif percentage >= TIER_PARTIAL_THRESHOLD:
        tier = "partial"     # 1 item, up to $15
    else:
        tier = "none"

    return {
        "student_record_id": student_record_id,
        "year": year,
        "month": month,
        "core_points": core_points,
        "core_max": core_max,
        "percentage": percentage,
        "bonus_points": bonus_points,
        "total_points": core_points + bonus_points,
        "tier": tier,
        "weeks_submitted": len(weeks_seen),
        "weeks_missing": weeks_missing,
        "wishlist_links": wishlist_links,
    }


def this_monday() -> str:
    today = date.today()
    monday = today.fromordinal(today.toordinal() - today.weekday())
    return monday.isoformat()