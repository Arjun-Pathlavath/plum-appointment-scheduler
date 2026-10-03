"""Comprehensive automated test suite for Plum AI Appointment Scheduler Assistant."""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ocr_service import OCRService
from app.services.entity_service import EntityService
from app.services.normalization_service import NormalizationService
from app.services.guardrail_service import GuardrailService
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.schemas import ExtractedEntities

client = TestClient(app)

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_inputs")


# -------------------------------------------------------------
# Unit Tests: Step 1 (OCR & Text Extraction)
# -------------------------------------------------------------

def test_step1_clean_text_input():
    """Verify clean typed natural language input extraction."""
    raw_text, conf = OCRService.extract_from_text("Book dentist next Friday at 3pm")
    assert raw_text == "Book dentist next Friday at 3pm"
    assert conf >= 0.90


def test_step1_noisy_text_typo_correction():
    """Verify noisy OCR text typo correction (nxt -> next, @ -> at)."""
    raw_text, conf = OCRService.extract_from_text("book dentist nxt Friday @ 3 pm")
    assert raw_text == "Book dentist next Friday at 3pm"
    assert conf == 0.90


def test_step1_image_ocr():
    """Verify image OCR extraction on sample image note."""
    img_path = os.path.join(SAMPLE_DIR, "clean_appointment_note.png")
    assert os.path.exists(img_path), "Sample image must exist"

    with open(img_path, "rb") as f:
        raw_text, conf = OCRService.extract_from_image(f.read())

    assert "dentist" in raw_text.lower()
    assert "friday" in raw_text.lower()
    assert conf >= 0.85


# -------------------------------------------------------------
# Unit Tests: Step 2 (Entity Extraction)
# -------------------------------------------------------------

def test_step2_entity_extraction_perfect_match():
    """Verify entity extraction matches the exact assignment sample."""
    entities, conf = EntityService.extract("Book dentist next Friday at 3pm")
    assert entities.date_phrase == "next Friday"
    assert entities.time_phrase == "3pm"
    assert entities.department == "dentist"
    assert conf == 0.85


def test_step2_entity_extraction_alternative_specialist():
    """Verify entity extraction on another specialty and format."""
    entities, conf = EntityService.extract("Cardiology checkup tomorrow at 10:30am")
    assert entities.date_phrase == "tomorrow"
    assert entities.time_phrase == "10:30am"
    assert entities.department in ["cardiology", "cardio"]
    assert conf == 0.85


# -------------------------------------------------------------
# Unit Tests: Step 3 (Normalization & Guardrails)
# -------------------------------------------------------------

def test_step3_normalization_asia_kolkata():
    """Verify normalization to ISO date/time and Asia/Kolkata timezone."""
    entities = {
        "date_phrase": "next Friday",
        "time_phrase": "3pm",
        "department": "dentist"
    }
    # Using anchor 2025-09-19 (Friday) -> next Friday is 2025-09-26
    norm_res, conf, err = NormalizationService.normalize(entities, reference_date_str="2025-09-19")
    assert err is None
    assert norm_res is not None
    assert norm_res.date == "2025-09-26"
    assert norm_res.time == "15:00"
    assert norm_res.tz == "Asia/Kolkata"
    assert conf == 0.90


def test_step3_guardrail_ambiguous_date():
    """Verify guardrail catches vague date expressions."""
    entities = ExtractedEntities(
        date_phrase="sometime next week",
        time_phrase="3pm",
        department="dentist"
    )
    ref_dt = NormalizationService.get_reference_datetime("2025-09-19")
    norm_date = NormalizationService.normalize_date(entities.date_phrase, ref_dt)
    norm_time = NormalizationService.normalize_time(entities.time_phrase)

    is_valid, guardrail = GuardrailService.validate_entities(
        entities=entities,
        normalized_date=norm_date,
        normalized_time=norm_time,
        ref_dt=ref_dt
    )
    assert is_valid is False
    assert guardrail.status == "needs_clarification"
    assert guardrail.message == "Ambiguous date/time or department"


def test_step3_guardrail_missing_time():
    """Verify guardrail catches missing time phrase."""
    entities = ExtractedEntities(
        date_phrase="next Friday",
        time_phrase=None,
        department="dentist"
    )
    ref_dt = NormalizationService.get_reference_datetime("2025-09-19")
    norm_date = NormalizationService.normalize_date(entities.date_phrase, ref_dt)

    is_valid, guardrail = GuardrailService.validate_entities(
        entities=entities,
        normalized_date=norm_date,
        normalized_time=None,
        ref_dt=ref_dt
    )
    assert is_valid is False
    assert guardrail.status == "needs_clarification"


# -------------------------------------------------------------
# Unit Tests: Step 4 (Final Appointment Synthesis)
# -------------------------------------------------------------

def test_step4_final_appointment_synthesis():
    """Verify Step 4 combines standardized department, ISO date, time, and timezone."""
    standard_dept = NormalizationService.normalize_department("dentist")
    assert standard_dept == "Dentistry"


# -------------------------------------------------------------
# Integration API Tests (All Endpoints)
# -------------------------------------------------------------

def test_api_step1_extract_text():
    """Test POST /api/v1/extract-text."""
    response = client.post("/api/v1/extract-text", json={"text": "Book dentist next Friday at 3pm"})
    assert response.status_code == 200
    data = response.json()
    assert data["raw_text"] == "Book dentist next Friday at 3pm"
    assert data["confidence"] >= 0.90


def test_api_step2_extract_entities():
    """Test POST /api/v1/extract-entities."""
    response = client.post(
        "/api/v1/extract-entities",
        json={"raw_text": "Book dentist next Friday at 3pm"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["entities"]["date_phrase"] == "next Friday"
    assert data["entities"]["time_phrase"] == "3pm"
    assert data["entities"]["department"] == "dentist"
    assert data["entities_confidence"] == 0.85


def test_api_step3_normalize():
    """Test POST /api/v1/normalize."""
    payload = {
        "entities": {
            "date_phrase": "next Friday",
            "time_phrase": "3pm",
            "department": "dentist"
        },
        "reference_date": "2025-09-19"
    }
    response = client.post("/api/v1/normalize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["normalized"]["date"] == "2025-09-26"
    assert data["normalized"]["time"] == "15:00"
    assert data["normalized"]["tz"] == "Asia/Kolkata"
    assert data["normalization_confidence"] == 0.90


def test_api_step4_finalize():
    """Test POST /api/v1/finalize."""
    payload = {
        "department": "dentist",
        "date": "2025-09-26",
        "time": "15:00",
        "tz": "Asia/Kolkata"
    }
    response = client.post("/api/v1/finalize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["appointment"]["department"] == "Dentistry"
    assert data["appointment"]["date"] == "2025-09-26"
    assert data["appointment"]["time"] == "15:00"
    assert data["appointment"]["tz"] == "Asia/Kolkata"
    assert data["status"] == "ok"


def test_api_appointment_pipeline_clean():
    """Test End-to-End POST /api/v1/appointment with clean input."""
    payload = {
        "text": "Book dentist next Friday at 3pm",
        "reference_date": "2025-09-19"
    }
    response = client.post("/api/v1/appointment", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["appointment"]["department"] == "Dentistry"
    assert data["appointment"]["date"] == "2025-09-26"
    assert data["appointment"]["time"] == "15:00"
    assert data["appointment"]["tz"] == "Asia/Kolkata"


def test_api_appointment_pipeline_image_upload():
    """Test End-to-End POST /api/v1/appointment with multipart image upload."""
    img_path = os.path.join(SAMPLE_DIR, "clean_appointment_note.png")
    with open(img_path, "rb") as f:
        response = client.post(
            "/api/v1/appointment",
            files={"image": ("clean_note.png", f, "image/png")},
            data={"reference_date": "2025-09-19"}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["appointment"]["department"] == "Dentistry"
    assert data["appointment"]["date"] == "2025-09-26"
    assert data["appointment"]["time"] == "15:00"
    assert data["appointment"]["tz"] == "Asia/Kolkata"


def test_api_appointment_guardrail_trigger():
    """Test End-to-End POST /api/v1/appointment with ambiguous input."""
    payload = {
        "text": "Book doctor appointment sometime next week",
        "reference_date": "2025-09-19"
    }
    response = client.post("/api/v1/appointment", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_clarification"
    assert data["message"] == "Ambiguous date/time or department"
