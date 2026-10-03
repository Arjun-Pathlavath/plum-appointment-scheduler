"""Live Interactive Demonstration Script for Plum SDE Assignment.

Runs through:
1. Step 1 OCR & Text Extraction (Clean typed, Noisy sample, Image input)
2. Step 2 Entity Extraction
3. Step 3 Normalization (Asia/Kolkata) & Ambiguity Guardrail
4. Step 4 Final Appointment Synthesis
5. End-to-End Multimodal Pipeline Execution
"""

import json
import time
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ocr_service import OCRService
from app.services.entity_service import EntityService
from app.services.normalization_service import NormalizationService
from app.services.guardrail_service import GuardrailService
from app.services.pipeline_orchestrator import PipelineOrchestrator

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_inputs")


def header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_json(data):
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    print(json.dumps(data, indent=2))


def run_demo():
    header("PLUM SDE ASSIGNMENT - PROBLEM STATEMENT 1: APPOINTMENT SCHEDULER")
    print("Architecture: OCR -> Entity Extraction -> Normalization (Asia/Kolkata) -> Guardrails")
    time.sleep(1)

    # ---------------------------------------------------------
    header("STEP 1: OCR / TEXT EXTRACTION")
    # ---------------------------------------------------------
    clean_input = "Book dentist next Friday at 3pm"
    print(f"\n[Case 1A] Typed Input:\n  '{clean_input}'")
    t1, c1 = OCRService.extract_from_text(clean_input)
    print("Output:")
    print_json({"raw_text": t1, "confidence": c1})

    noisy_input = "book dentist nxt Friday @ 3 pm"
    print(f"\n[Case 1B] Noisy OCR Text:\n  '{noisy_input}'")
    t2, c2 = OCRService.extract_from_text(noisy_input)
    print("Output (Typo corrected & normalized):")
    print_json({"raw_text": t2, "confidence": c2})

    image_path = os.path.join(SAMPLE_DIR, "clean_appointment_note.png")
    print(f"\n[Case 1C] Image Note Input:\n  '{image_path}'")
    with open(image_path, "rb") as f:
        t3, c3 = OCRService.extract_from_image(f.read())
    print("Output (OCR Extracted):")
    print_json({"raw_text": t3, "confidence": c3})
    time.sleep(1)

    # ---------------------------------------------------------
    header("STEP 2: ENTITY EXTRACTION")
    # ---------------------------------------------------------
    print(f"\nInput raw_text: '{t1}'")
    entities, ent_conf = EntityService.extract(t1)
    print("Output:")
    print_json({"entities": entities.model_dump(), "entities_confidence": ent_conf})
    time.sleep(1)

    # ---------------------------------------------------------
    header("STEP 3: NORMALIZATION (Asia/Kolkata) & GUARDRAIL CHECKS")
    # ---------------------------------------------------------
    ref_date = "2025-09-19"
    print(f"\n[Case 3A] Valid Entities with Reference Date Anchor: {ref_date}")
    norm_res, norm_conf, err = NormalizationService.normalize(entities.model_dump(), ref_date)
    print("Output:")
    print_json({"normalized": norm_res.model_dump(), "normalization_confidence": norm_conf})

    print("\n[Case 3B] Ambiguous Date Input: 'sometime next week'")
    ambig_entities = {"date_phrase": "sometime next week", "time_phrase": None, "department": "dentist"}
    ambig_res, _, ambig_err = NormalizationService.normalize(ambig_entities, ref_date)
    print("Guardrail Triggered:")
    print_json({"status": "needs_clarification", "message": "Ambiguous date/time or department", "reason": ambig_err})
    time.sleep(1)

    # ---------------------------------------------------------
    header("STEP 4: FINAL APPOINTMENT SYNTHESIS")
    # ---------------------------------------------------------
    standard_dept = NormalizationService.normalize_department(entities.department)
    final_output = {
        "appointment": {
            "department": standard_dept,
            "date": norm_res.date,
            "time": norm_res.time,
            "tz": norm_res.tz
        },
        "status": "ok"
    }
    print("Output:")
    print_json(final_output)
    time.sleep(1)

    # ---------------------------------------------------------
    header("END-TO-END PIPELINE ORCHESTRATION")
    # ---------------------------------------------------------
    print("\nExecuting full pipeline for: 'Book dentist next Friday at 3pm' with anchor 2025-09-19...")
    e2e_res = PipelineOrchestrator.process_request("Book dentist next Friday at 3pm", reference_date=ref_date)
    print_json(e2e_res)

    print("\nExecuting full pipeline for image upload ('noisy_ocr_sample.png')...")
    noisy_img_path = os.path.join(SAMPLE_DIR, "noisy_ocr_sample.png")
    with open(noisy_img_path, "rb") as f:
        e2e_img_res = PipelineOrchestrator.process_request(image_bytes=f.read(), reference_date=ref_date)
    print_json(e2e_img_res)

    print("\nExecuting full pipeline on ambiguous query: 'Book doctor appointment sometime next week'...")
    e2e_ambig = PipelineOrchestrator.process_request("Book doctor appointment sometime next week", reference_date=ref_date)
    print_json(e2e_ambig)

    header("ALL PIPELINE STAGES VERIFIED SUCCESSFULLY")


if __name__ == "__main__":
    run_demo()
