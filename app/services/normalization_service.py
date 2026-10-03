"""Normalization Service (Step 3).

Normalizes extracted date and time phrases into ISO 8601 strings in the Asia/Kolkata timezone,
and normalizes medical department names according to clinical taxonomy.
"""

import re
from datetime import datetime, timedelta
import zoneinfo
import logging
from typing import Tuple, Optional, Dict, Any
from dateutil import parser as date_parser

from app.config import DEFAULT_TIMEZONE, DEPARTMENT_TAXONOMY
from app.schemas import NormalizedDateTime

logger = logging.getLogger(__name__)

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


class NormalizationService:
    """Service to normalize date, time, and department entities."""

    @classmethod
    def get_reference_datetime(cls, reference_date_str: Optional[str] = None) -> datetime:
        """Get current reference datetime localized to Asia/Kolkata."""
        kolkata_tz = zoneinfo.ZoneInfo(DEFAULT_TIMEZONE)
        if reference_date_str:
            try:
                # If date-only string provided, assume 09:00 AM on that date in Asia/Kolkata
                parsed = date_parser.parse(reference_date_str)
                return parsed.replace(tzinfo=kolkata_tz)
            except Exception as e:
                logger.warning(f"Could not parse reference_date '{reference_date_str}': {e}")

        # Default to now in Asia/Kolkata
        return datetime.now(kolkata_tz)

    @classmethod
    def normalize_date(cls, date_phrase: Optional[str], ref_dt: datetime) -> Optional[str]:
        """Normalize relative and absolute date phrases to ISO YYYY-MM-DD."""
        if not date_phrase:
            return None

        clean_phrase = date_phrase.strip().lower()

        # Handle vague phrases that should trigger guardrails
        if any(vague in clean_phrase for vague in ["sometime", "next week", "this week", "later", "anytime"]):
            return None

        # Relative single-day offsets
        if clean_phrase in ["today"]:
            return ref_dt.strftime("%Y-%m-%d")
        if clean_phrase in ["tomorrow", "tmrw", "tmro"]:
            return (ref_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        if clean_phrase in ["day after tomorrow"]:
            return (ref_dt + timedelta(days=2)).strftime("%Y-%m-%d")

        # Weekday matching: "next Friday", "this Friday", "coming Friday", "Friday"
        weekday_match = re.search(r"\b(next|this|coming)?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", clean_phrase)
        if weekday_match:
            modifier = weekday_match.group(1) or ""
            target_day_name = weekday_match.group(2)
            target_weekday = WEEKDAYS[target_day_name]
            current_weekday = ref_dt.weekday()

            if modifier == "next":
                # "next Friday" in conversational English usually means the Friday of the following week
                days_ahead = (target_weekday - current_weekday) % 7
                if days_ahead == 0:
                    days_ahead = 7
                else:
                    days_ahead += 7
                return (ref_dt + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            elif modifier in ["this", "coming"]:
                days_ahead = (target_weekday - current_weekday) % 7
                if days_ahead == 0:
                    days_ahead = 7
                return (ref_dt + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            else:
                # Just weekday name, e.g. "Friday"
                days_ahead = (target_weekday - current_weekday) % 7
                if days_ahead == 0:
                    days_ahead = 7
                return (ref_dt + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        # Try parsing standard absolute date strings
        try:
            parsed = date_parser.parse(clean_phrase, default=ref_dt, fuzzy=True)
            return parsed.strftime("%Y-%m-%d")
        except Exception:
            return None

    @classmethod
    def normalize_time(cls, time_phrase: Optional[str]) -> Optional[str]:
        """Normalize time strings (e.g. '3pm', '15:00', 'morning 10am') to 24-hr HH:MM."""
        if not time_phrase:
            return None

        clean_time = time_phrase.strip().lower()

        # Handle noon / midnight
        if "noon" in clean_time:
            return "12:00"
        if "midnight" in clean_time:
            return "00:00"

        # Regex for 12-hour or 24-hour patterns
        match_12hr = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", clean_time)
        if match_12hr:
            hour = int(match_12hr.group(1))
            minute = int(match_12hr.group(2)) if match_12hr.group(2) else 0
            meridiem = match_12hr.group(3)

            if meridiem == "pm" and hour < 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0
            return f"{hour:02d}:{minute:02d}"

        # 24-hour pattern: "15:00"
        match_24hr = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", clean_time)
        if match_24hr:
            hour = int(match_24hr.group(1))
            minute = int(match_24hr.group(2))
            return f"{hour:02d}:{minute:02d}"

        # Fuzzy dateutil fallback
        try:
            parsed = date_parser.parse(clean_time)
            return parsed.strftime("%H:%M")
        except Exception:
            return None

    @classmethod
    def normalize_department(cls, department: Optional[str]) -> Optional[str]:
        """Normalize raw department string to standard clinical taxonomy name."""
        if not department:
            return None
        dept_clean = department.strip().lower()
        return DEPARTMENT_TAXONOMY.get(dept_clean, department.title())

    @classmethod
    def normalize(
        cls,
        entities: Dict[str, Optional[str]],
        reference_date_str: Optional[str] = None
    ) -> Tuple[Optional[NormalizedDateTime], float, Optional[str]]:
        """
        Normalize entities into ISO date, 24-hr time, and Asia/Kolkata timezone.
        Returns: (NormalizedDateTime, confidence, error_reason)
        """
        ref_dt = cls.get_reference_datetime(reference_date_str)

        date_phrase = entities.get("date_phrase")
        time_phrase = entities.get("time_phrase")
        department = entities.get("department")

        normalized_date = cls.normalize_date(date_phrase, ref_dt)
        normalized_time = cls.normalize_time(time_phrase)

        # Ambiguity checks
        reasons = []
        if not normalized_date:
            reasons.append("Missing or ambiguous date_phrase")
        if not normalized_time:
            reasons.append("Missing or ambiguous time_phrase")
        if not department:
            reasons.append("Missing or ambiguous department")

        if reasons:
            return None, 0.0, "; ".join(reasons)

        normalized_obj = NormalizedDateTime(
            date=normalized_date,
            time=normalized_time,
            tz=DEFAULT_TIMEZONE
        )
        return normalized_obj, 0.90, None
