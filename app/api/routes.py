"""API routes exposing Step 1, Step 2, Step 3, Step 4, and the complete Appointment pipeline."""

from typing import Optional, Union, Dict, Any
from fastapi import APIRouter, Request, HTTPException, Query
from app.schemas import (
    TextExtractionRequest,
    EntityExtractionRequest,
    NormalizationRequest,
    FinalizeRequest,
    Step1Response,
    Step2Response,
    Step3Response,
    Step4Response,
    GuardrailExitCondition,
    FullPipelineResponse,
    ExtractedEntities,
    AppointmentDetails
)
from app.services.ocr_service import OCRService
from app.services.entity_service import EntityService
from app.services.normalization_service import NormalizationService
from app.services.guardrail_service import GuardrailService
from app.services.pipeline_orchestrator import PipelineOrchestrator

router = APIRouter(prefix="/api/v1", tags=["Appointment Scheduler"])


# -------------------------------------------------------------
# Step 1: OCR / Text Extraction
# -------------------------------------------------------------
@router.post(
    "/extract-text",
    response_model=Step1Response,
    summary="Step 1: Extract and clean raw text from typed input or image"
)
async def extract_text(request: Request):
    """
    Step 1 of the pipeline:
    - Accepts typed text via JSON body or form field.
    - Accepts photos/scanned notes via multipart file upload ('image').
    - Cleans noise and minor OCR typos (e.g. 'nxt' -> 'next', '@' -> 'at').
    - Returns raw_text and confidence score.
    """
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        image_file = form.get("image")
        if image_file and hasattr(image_file, "read"):
            image_bytes = await image_file.read()
            raw_text, confidence = OCRService.extract_from_image(image_bytes)
            return Step1Response(raw_text=raw_text, confidence=confidence)

        text = form.get("text")
        if text:
            raw_text, confidence = OCRService.extract_from_text(str(text))
            return Step1Response(raw_text=raw_text, confidence=confidence)
    else:
        try:
            body = await request.json()
            text = body.get("text")
            if text:
                raw_text, confidence = OCRService.extract_from_text(text)
                return Step1Response(raw_text=raw_text, confidence=confidence)
        except Exception:
            pass

    raise HTTPException(status_code=400, detail="Either 'text' or an 'image' file must be provided.")


# -------------------------------------------------------------
# Step 2: Entity Extraction
# -------------------------------------------------------------
@router.post(
    "/extract-entities",
    response_model=Step2Response,
    summary="Step 2: Extract date/time phrases and department from raw text"
)
async def extract_entities(payload: EntityExtractionRequest):
    """
    Step 2 of the pipeline:
    - Extracts date_phrase, time_phrase, and medical department.
    - Computes entities_confidence.
    """
    entities, confidence = EntityService.extract(payload.raw_text)
    return Step2Response(entities=entities, entities_confidence=confidence)


# -------------------------------------------------------------
# Step 3: Normalization & Guardrail Check
# -------------------------------------------------------------
@router.post(
    "/normalize",
    response_model=Union[Step3Response, GuardrailExitCondition],
    summary="Step 3: Map phrases to ISO date/time in Asia/Kolkata timezone with guardrails"
)
async def normalize(payload: NormalizationRequest):
    """
    Step 3 of the pipeline:
    - Normalizes relative and absolute dates to ISO YYYY-MM-DD.
    - Normalizes times to 24-hr ISO HH:MM.
    - Enforces Asia/Kolkata timezone.
    - Evaluates ambiguity guardrails; if ambiguous, returns exit condition.
    """
    raw_entities = ExtractedEntities(
        date_phrase=payload.entities.get("date_phrase"),
        time_phrase=payload.entities.get("time_phrase"),
        department=payload.entities.get("department")
    )

    ref_dt = NormalizationService.get_reference_datetime(payload.reference_date)
    norm_date = NormalizationService.normalize_date(raw_entities.date_phrase, ref_dt)
    norm_time = NormalizationService.normalize_time(raw_entities.time_phrase)

    is_valid, guardrail_exit = GuardrailService.validate_entities(
        entities=raw_entities,
        normalized_date=norm_date,
        normalized_time=norm_time,
        ref_dt=ref_dt
    )

    if not is_valid:
        return guardrail_exit

    return Step3Response(
        normalized={
            "date": norm_date,
            "time": norm_time,
            "tz": "Asia/Kolkata"
        },
        normalization_confidence=0.90
    )


# -------------------------------------------------------------
# Step 4: Final Appointment JSON
# -------------------------------------------------------------
@router.post(
    "/finalize",
    response_model=Step4Response,
    summary="Step 4: Combine entities and normalized values into final appointment JSON"
)
async def finalize(payload: FinalizeRequest):
    """
    Step 4 of the pipeline:
    - Combines standardized department name, date, time, and timezone.
    - Returns final appointment record with status 'ok'.
    """
    standard_dept = NormalizationService.normalize_department(payload.department)
    return Step4Response(
        appointment=AppointmentDetails(
            department=standard_dept or payload.department.title(),
            date=payload.date,
            time=payload.time,
            tz=payload.tz or "Asia/Kolkata"
        ),
        status="ok"
    )


# -------------------------------------------------------------
# End-to-End Orchestrated Pipeline
# -------------------------------------------------------------
@router.post(
    "/appointment",
    response_model=Union[Step4Response, FullPipelineResponse, GuardrailExitCondition],
    summary="End-to-End AI-Powered Appointment Scheduler Pipeline"
)
async def schedule_appointment(
    request: Request,
    include_stages: bool = Query(
        default=False,
        description="Include full pipeline audit stages (Step 1, 2, 3) in addition to appointment"
    )
):
    """
    End-to-End Orchestrated Appointment Scheduler:
    - Ingests natural language text or scanned image note.
    - Chains Step 1 (OCR) -> Step 2 (Entity Extraction) -> Step 3 (Normalization).
    - Checks Guardrails: If date, time, or department is ambiguous, returns standard clarification exit.
    - Completes Step 4: Generates final structured appointment JSON.
    """
    content_type = request.headers.get("content-type", "")
    text_content = None
    image_bytes = None
    ref_date = None

    if "multipart/form-data" in content_type:
        form = await request.form()
        image_file = form.get("image")
        if image_file and hasattr(image_file, "read"):
            image_bytes = await image_file.read()
        if form.get("text"):
            text_content = str(form.get("text"))
        if form.get("reference_date"):
            ref_date = str(form.get("reference_date"))
    else:
        try:
            body = await request.json()
            text_content = body.get("text")
            ref_date = body.get("reference_date")
        except Exception:
            pass

    result = PipelineOrchestrator.process_request(
        text_input=text_content,
        image_bytes=image_bytes,
        reference_date=ref_date,
        include_stages=include_stages
    )
    return result
