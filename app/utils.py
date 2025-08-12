from __future__ import annotations

from datetime import date
from typing import Optional


def compute_age(dob: Optional[date]) -> Optional[int]:
    if not dob:
        return None
    today = date.today()
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return years


def age_band(age: Optional[int]) -> Optional[str]:
    if age is None:
        return None
    if age < 18:
        return "under_18"
    bands = [(18, 24), (25, 34), (35, 44), (45, 54), (55, 64)]
    for lo, hi in bands:
        if lo <= age <= hi:
            return f"{lo}_{hi}"
    return "65_plus"


def compute_demographic_segment(dob: Optional[date], gender: Optional[str]) -> Optional[str]:
    a = compute_age(dob)
    b = age_band(a)
    if not b and not gender:
        return None
    normalized_gender = (gender or "other").strip().lower()
    return f"{normalized_gender}_{b or 'unknown'}"


