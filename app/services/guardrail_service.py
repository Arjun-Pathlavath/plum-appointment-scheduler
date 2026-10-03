"""Guardrail Service for Appointment Scheduler Assistant.

Detects ambiguity, incomplete slots, past dates, or non-actionable inputs,
and returns standard exit conditions matching the problem statement specification.
"""

from typing import Dict, Optional, Tuple, Any
from datetime import datetime
from app.schemas import GuardrailExitCondition, ExtractedEntities


class GuardrailService:
    """Service implementing guardrails and exit conditions."""

    @classmethod
    def validate_entities(
        cls,
        entities: ExtractedEntities,
        normalized_date: Optional[str] = None,
        normalized_time: Optional[str] = None,
        ref_dt: Optional[datetime] = None
    ) -> Tuple[bool, Optional[GuardrailExitCondition]]:
        """
        Validate whether the appointment request meets all clarity requirements.
        Returns: (is_valid, guardrail_exit_condition)
        """
        missing_reasons = []

        # Check department
        if not entities.department:
            missing_reasons.append("Medical department is missing or could not be identified")

        # Check date
        if not entities.date_phrase or not normalized_date:
            missing_reasons.append("Date phrase is missing, vague, or cannot be resolved to a specific day")

        # Check time
        if not entities.time_phrase or not normalized_time:
            missing_reasons.append("Time phrase is missing or ambiguous (e.g. no specific hour/period)")

        # Check if resolved date is in the past
        if normalized_date and ref_dt:
            try:
                target_dt = datetime.strptime(normalized_date, "%Y-%m-%d").date()
                if target_dt < ref_dt.date():
                    missing_reasons.append(f"Requested appointment date {normalized_date} is in the past")
            except Exception:
                pass

        if missing_reasons:
            exit_condition = GuardrailExitCondition(
                status="needs_clarification",
                message="Ambiguous date/time or department",
                details={"reasons": missing_reasons}
            )
            return False, exit_condition

        return True, None
