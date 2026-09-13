"""
Functions specific to the Students table.
"""

import os
from airtable_client import list_records, create_record, update_record

TABLE_NAME = os.getenv("AIRTABLE_STUDENTS_TABLE", "Students")


def get_all_students(active_only: bool = True) -> list[dict]:
    formula = "{Active} = TRUE()" if active_only else None
    return list_records(TABLE_NAME, formula=formula)


def get_students_by_group(group_name: str) -> list[dict]:
    return list_records(TABLE_NAME, formula=f"{{Group Name}} = '{group_name}'")


def get_all_group_names(active_only: bool = True) -> list[str]:
    """Distinct group names, for a group-selection dropdown."""
    students = get_all_students(active_only=active_only)
    groups = {s["fields"].get("Group Name") for s in students if s["fields"].get("Group Name")}
    return sorted(groups)


def get_nickname_map_for_group(group_name: str, active_only: bool = True) -> dict:
    """Returns {nickname: record_id} for students in a given group."""
    students = get_students_by_group(group_name)
    if active_only:
        students = [s for s in students if s["fields"].get("Active")]
    return {
        s["fields"]["Nickname"]: s["id"]
        for s in students
        if s["fields"].get("Nickname")
    }


def get_students_map_for_group(group_name: str, active_only: bool = True) -> dict:
    """
    Returns {nickname: {"id": record_id, "pin": pin}} for students in a
    given group. Used by Student Check-in to verify a student's own PIN
    before recording a check-in under their name — since check-ins now
    feed into the monthly points/reward system, this stops one student
    from submitting (accidentally or otherwise) as someone else.
    """
    students = get_students_by_group(group_name)
    if active_only:
        students = [s for s in students if s["fields"].get("Active")]
    return {
        s["fields"]["Nickname"]: {"id": s["id"], "pin": s["fields"].get("PIN", "")}
        for s in students
        if s["fields"].get("Nickname")
    }


def add_student(name: str, group_name: str) -> dict:
    fields = {
        "Name": name,
        "Group Name": group_name,
        "Active": True,
    }
    return create_record(TABLE_NAME, fields)


def deactivate_student(record_id: str) -> dict:
    return update_record(TABLE_NAME, record_id, {"Active": False})