"""Pydantic schemas adhering strictly to Plum SDE Assignment Problem Statement 1 contracts."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# Input Requests
# -------------------------------------------------------------

class TextExtractionRequest(BaseModel):
    text: Optional[str] = Field(default=None, description="Typed natural language text")
    reference_date: Optional[str] = Field(
        default=None,
        description="Optional ISO reference date for relative calendar calculations (e.g. '2025-09-19')"
    )


class EntityExtractionRequest(BaseModel):
    raw_text: str = Field(..., description="Raw text obtained from OCR or typed input")


class NormalizationRequest(BaseModel):
    entities: Dict[str, Optional[str]] = Field(
        ...,
        description="Extracted entities containing date_phrase, time_phrase, and department"
    )
    reference_date: Optional[str] = Field(
        default=None,
        description="Optional ISO reference date for relative calculations (default: current date in Asia/Kolkata)"
    )


class FinalizeRequest(BaseModel):
    department: str = Field(..., description="Department or specialist name")
    date: str = Field(..., description="Normalized ISO date (YYYY-MM-DD)")
    time: str = Field(..., description="Normalized 24-hr time (HH:MM)")
    tz: str = Field(default="Asia/Kolkata", description="Timezone name")


# -------------------------------------------------------------
# Step 1: OCR / Text Extraction
# -------------------------------------------------------------

class Step1Response(BaseModel):
    raw_text: str = Field(..., description="Extracted raw text with minor typo normalization")
    confidence: float = Field(..., ge=0.0, le=1.0, description="OCR / parsing confidence score")


# -------------------------------------------------------------
# Step 2: Entity Extraction
# -------------------------------------------------------------

class ExtractedEntities(BaseModel):
    date_phrase: Optional[str] = Field(default=None, description="Extracted date phrase (e.g. 'next Friday')")
    time_phrase: Optional[str] = Field(default=None, description="Extracted time phrase (e.g. '3pm')")
    department: Optional[str] = Field(default=None, description="Extracted department (e.g. 'dentist')")


class Step2Response(BaseModel):
    entities: ExtractedEntities
    entities_confidence: float = Field(..., ge=0.0, le=1.0, description="Entity extraction confidence")


# -------------------------------------------------------------
# Step 3: Normalization & Guardrails
# -------------------------------------------------------------

class NormalizedDateTime(BaseModel):
    date: str = Field(..., description="ISO 8601 date string (YYYY-MM-DD)")
    time: str = Field(..., description="24-hour time string (HH:MM)")
    tz: str = Field(default="Asia/Kolkata", description="Timezone name")


class Step3Response(BaseModel):
    normalized: NormalizedDateTime
    normalization_confidence: float = Field(..., ge=0.0, le=1.0, description="Normalization confidence")


class GuardrailExitCondition(BaseModel):
    status: str = Field(default="needs_clarification", description="Guardrail status")
    message: str = Field(default="Ambiguous date/time or department", description="Clarification explanation")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Detailed diagnostic reasons")


# -------------------------------------------------------------
# Step 4: Final Appointment JSON
# -------------------------------------------------------------

class AppointmentDetails(BaseModel):
    department: str = Field(..., description="Standardized clinical department name (e.g. 'Dentistry')")
    date: str = Field(..., description="ISO date (YYYY-MM-DD)")
    time: str = Field(..., description="ISO 24-hr time (HH:MM)")
    tz: str = Field(default="Asia/Kolkata", description="Target timezone")


class Step4Response(BaseModel):
    appointment: AppointmentDetails
    status: str = Field(default="ok", description="Appointment status")


# -------------------------------------------------------------
# Full Pipeline Output
# -------------------------------------------------------------

class PipelineStages(BaseModel):
    step1_ocr: Step1Response
    step2_entities: Step2Response
    step3_normalization: Step3Response


class FullPipelineResponse(BaseModel):
    appointment: AppointmentDetails
    status: str = Field(default="ok")
    pipeline_stages: Optional[PipelineStages] = None
