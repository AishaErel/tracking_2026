"""
Functions specific to the WishlistItems table.

Note: "Student Name" is a Link to another record field, so it expects a
LIST of record IDs, e.g. ["recXXXXXXXX"].

This table replaces the earlier "Wishlist Link This Week" field on
StudentsCheckins — items now persist across weeks (with history, editing,
and deletion) instead of being overwritten every submission.
"""

import os
import calendar
from datetime import date
from airtable_client import list_records, create_record, update_record, delete_record

TABLE_NAME = os.getenv("AIRTABLE_WISHLIST_TABLE", "WishlistItems")


def add_wishlist_item(student_record_id: str, item_link: str, item_price: float, week_added: str) -> dict:
    fields = {
        "Student Name": [student_record_id],
        "Item Link": item_link,
        "Item Price": item_price,
        "Week Added": week_added,
        "Selected For Reward": False,
    }
    return create_record(TABLE_NAME, fields)


def get_wishlist_items_for_student(student_record_id: str) -> list[dict]:
    """All wishlist items ever added by a student, most recent first."""
    all_items = list_records(TABLE_NAME)
    items = [r for r in all_items if student_record_id in r["fields"].get("Student Name", [])]
    return sorted(items, key=lambda r: r["fields"].get("Week Added", ""), reverse=True)


def get_wishlist_items_for_student_month(student_record_id: str, year: int, month: int) -> list[dict]:
    """Only the items added within a given calendar month — used to scope
    what's selectable against that month's reward tier."""
    start = date(year, month, 1).isoformat()
    last_day = calendar.monthrange(year, month)[1]
    end = date(year, month, last_day).isoformat()

    items = get_wishlist_items_for_student(student_record_id)
    return [r for r in items if start <= r["fields"].get("Week Added", "") <= end]


def update_wishlist_item(record_id: str, fields: dict) -> dict:
    return update_record(TABLE_NAME, record_id, fields)


def delete_wishlist_item(record_id: str) -> dict:
    return delete_record(TABLE_NAME, record_id)