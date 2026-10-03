#!/usr/bin/env bash
# Quick curl test script for Plum AI Appointment Scheduler
BASE_URL="http://127.0.0.1:8000"

echo "=== 1. Health Check ==="
curl -s -X GET "$BASE_URL/health" | jq . || curl -s -X GET "$BASE_URL/health"
echo -e "\n"

echo "=== 2. Step 1: Extract Text (Clean Typed) ==="
curl -s -X POST "$BASE_URL/api/v1/extract-text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Book dentist next Friday at 3pm"}'
echo -e "\n"

echo "=== 3. Step 1: Extract Text (Noisy OCR Text) ==="
curl -s -X POST "$BASE_URL/api/v1/extract-text" \
  -H "Content-Type: application/json" \
  -d '{"text": "book dentist nxt Friday @ 3 pm"}'
echo -e "\n"

echo "=== 4. Step 1: Extract Text (Image Upload) ==="
curl -s -X POST "$BASE_URL/api/v1/extract-text" \
  -F "image=@sample_inputs/clean_appointment_note.png"
echo -e "\n"

echo "=== 5. Step 2: Entity Extraction ==="
curl -s -X POST "$BASE_URL/api/v1/extract-entities" \
  -H "Content-Type: application/json" \
  -d '{"raw_text": "Book dentist next Friday at 3pm"}'
echo -e "\n"

echo "=== 6. Step 3: Normalization (Asia/Kolkata) ==="
curl -s -X POST "$BASE_URL/api/v1/normalize" \
  -H "Content-Type: application/json" \
  -d '{"entities": {"date_phrase": "next Friday", "time_phrase": "3pm", "department": "dentist"}, "reference_date": "2025-09-19"}'
echo -e "\n"

echo "=== 7. Step 3: Ambiguity Guardrail Trigger ==="
curl -s -X POST "$BASE_URL/api/v1/normalize" \
  -H "Content-Type: application/json" \
  -d '{"entities": {"date_phrase": "sometime next week", "time_phrase": null, "department": "dentist"}, "reference_date": "2025-09-19"}'
echo -e "\n"

echo "=== 8. Step 4: Finalize Appointment ==="
curl -s -X POST "$BASE_URL/api/v1/finalize" \
  -H "Content-Type: application/json" \
  -d '{"department": "dentist", "date": "2025-09-26", "time": "15:00", "tz": "Asia/Kolkata"}'
echo -e "\n"

echo "=== 9. End-to-End Pipeline (Clean Text) ==="
curl -s -X POST "$BASE_URL/api/v1/appointment?include_stages=true" \
  -H "Content-Type: application/json" \
  -d '{"text": "Book dentist next Friday at 3pm", "reference_date": "2025-09-19"}'
echo -e "\n"

echo "=== 10. End-to-End Pipeline (Image Upload) ==="
curl -s -X POST "$BASE_URL/api/v1/appointment" \
  -F "image=@sample_inputs/noisy_ocr_sample.png" \
  -F "reference_date=2025-09-19"
echo -e "\n"

echo "=== 11. End-to-End Pipeline Guardrail Ambiguity Trigger ==="
curl -s -X POST "$BASE_URL/api/v1/appointment" \
  -H "Content-Type: application/json" \
  -d '{"text": "Doctor appointment sometime next week", "reference_date": "2025-09-19"}'
echo -e "\n"
