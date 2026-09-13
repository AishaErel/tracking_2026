"""
Functions specific to the Mentors table.
"""

import os
from airtable_client import list_records, create_record, update_record

TABLE_NAME = os.getenv("AIRTABLE_MENTORS_TABLE", "Mentors")


def get_all_mentors(active_only: bool = True) -> list[dict]:
    formula = "{Active} = TRUE()" if active_only else None
    return list_records(TABLE_NAME, formula=formula)


def get_mentor_by_email(email: str) -> dict | None:
    records = list_records(TABLE_NAME, formula=f"{{Email}} = '{email}'")
    return records[0] if records else None


def get_mentor_by_name(name: str) -> dict | None:
    """
    Looks up a single mentor by their Name field. Used by the Mentor
    Dashboard to fetch that mentor's Password and Group Name after they
    pick their name from a selectbox, so we can gate access to only
    their own group's student check-ins.
    """
    records = list_records(TABLE_NAME, formula=f"{{Name}} = '{name}'")
    return records[0] if records else None


def add_mentor(name: str, email: str, group_name: str, grade_level: str) -> dict:
    fields = {
        "Name": name,
        "Email": email,
        "Group Name": group_name,
        "Active": True,
    }
    return create_record(TABLE_NAME, fields)


def deactivate_mentor(record_id: str) -> dict:
    return update_record(TABLE_NAME, record_id, {"Active": False})