"""End-to-end Pipeline Orchestrator for Appointment Scheduler Assistant.

Chains Step 1 (OCR/Text Extraction), Step 2 (Entity Extraction),
Step 3 (Normalization), Guardrail Check, and Step 4 (Final Appointment JSON).
"""

from typing import Optional, Union, Dict, Any
from app.services.ocr_service import OCRService
from app.services.entity_service import EntityService
from app.services.normalization_service import NormalizationService
from app.services.guardrail_service import GuardrailService
from app.schemas import (
    Step1Response,
    Step2Response,
    Step3Response,
    Step4Response,
    AppointmentDetails,
    GuardrailExitCondition,
    PipelineStages,
    FullPipelineResponse
)


class PipelineOrchestrator:
    """Orchestrates the 4-step AI scheduling pipeline."""

    @classmethod
    def process_request(
        cls,
        text_input: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        reference_date: Optional[str] = None,
        include_stages: bool = False
    ) -> Union[FullPipelineResponse, GuardrailExitCondition, Step4Response]:
        """
        Execute full pipeline from raw input to final appointment JSON.
        """
        # --- Step 1: OCR / Text Extraction ---
        if image_bytes:
            raw_text, ocr_conf = OCRService.extract_from_image(image_bytes)
        elif text_input:
            raw_text, ocr_conf = OCRService.extract_from_text(text_input)
        else:
            return GuardrailExitCondition(
                status="needs_clarification",
                message="Ambiguous date/time or department",
                details={"reasons": ["No text or image input provided"]}
            )

        step1 = Step1Response(raw_text=raw_text, confidence=ocr_conf)

        if not raw_text or ocr_conf == 0.0:
            return GuardrailExitCondition(
                status="needs_clarification",
                message="Ambiguous date/time or department",
                details={"reasons": ["Could not extract readable text from document/input"]}
            )

        # --- Step 2: Entity Extraction ---
        entities, entities_conf = EntityService.extract(raw_text)
        step2 = Step2Response(entities=entities, entities_confidence=entities_conf)

        # --- Step 3: Normalization ---
        ref_dt = NormalizationService.get_reference_datetime(reference_date)
        normalized_date = NormalizationService.normalize_date(entities.date_phrase, ref_dt)
        normalized_time = NormalizationService.normalize_time(entities.time_phrase)
        standard_dept = NormalizationService.normalize_department(entities.department)

        # --- Guardrail Validation ---
        is_valid, guardrail_exit = GuardrailService.validate_entities(
            entities=entities,
            normalized_date=normalized_date,
            normalized_time=normalized_time,
            ref_dt=ref_dt
        )

        if not is_valid:
            return guardrail_exit

        normalized_obj = Step3Response(
            normalized={
                "date": normalized_date,
                "time": normalized_time,
                "tz": "Asia/Kolkata"
            },
            normalization_confidence=0.90
        )

        # --- Step 4: Final Appointment JSON ---
        appointment_data = AppointmentDetails(
            department=standard_dept or "General Medicine",
            date=normalized_date,
            time=normalized_time,
            tz="Asia/Kolkata"
        )

        if include_stages:
            return FullPipelineResponse(
                appointment=appointment_data,
                status="ok",
                pipeline_stages=PipelineStages(
                    step1_ocr=step1,
                    step2_entities=step2,
                    step3_normalization=normalized_obj
                )
            )

        return Step4Response(
            appointment=appointment_data,
            status="ok"
        )
