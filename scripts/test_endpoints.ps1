# PowerShell curl/Invoke-RestMethod test script for Plum AI Appointment Scheduler
$baseUrl = "http://127.0.0.1:8000"

Write-Host "`n=== 1. Health Check ===" -ForegroundColor Cyan
Invoke-RestMethod -Uri "$baseUrl/health" -Method Get | ConvertTo-Json

Write-Host "`n=== 2. Step 1: Extract Text (Clean Typed) ===" -ForegroundColor Cyan
Invoke-RestMethod -Uri "$baseUrl/api/v1/extract-text" -Method Post -ContentType "application/json" -Body '{"text": "Book dentist next Friday at 3pm"}' | ConvertTo-Json

Write-Host "`n=== 3. Step 1: Extract Text (Noisy OCR Sample) ===" -ForegroundColor Cyan
Invoke-RestMethod -Uri "$baseUrl/api/v1/extract-text" -Method Post -ContentType "application/json" -Body '{"text": "book dentist nxt Friday @ 3 pm"}' | ConvertTo-Json

Write-Host "`n=== 4. Step 2: Entity Extraction ===" -ForegroundColor Cyan
Invoke-RestMethod -Uri "$baseUrl/api/v1/extract-entities" -Method Post -ContentType "application/json" -Body '{"raw_text": "Book dentist next Friday at 3pm"}' | ConvertTo-Json

Write-Host "`n=== 5. Step 3: Normalization (Asia/Kolkata) ===" -ForegroundColor Cyan
$normPayload = @{
    entities = @{
        date_phrase = "next Friday"
        time_phrase = "3pm"
        department = "dentist"
    }
    reference_date = "2025-09-19"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$baseUrl/api/v1/normalize" -Method Post -ContentType "application/json" -Body $normPayload | ConvertTo-Json

Write-Host "`n=== 6. Step 3: Ambiguity Guardrail Trigger ===" -ForegroundColor Cyan
$ambigPayload = @{
    entities = @{
        date_phrase = "sometime next week"
        time_phrase = $null
        department = "dentist"
    }
    reference_date = "2025-09-19"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$baseUrl/api/v1/normalize" -Method Post -ContentType "application/json" -Body $ambigPayload | ConvertTo-Json

Write-Host "`n=== 7. Step 4: Finalize Appointment ===" -ForegroundColor Cyan
$finalPayload = @{
    department = "dentist"
    date = "2025-09-26"
    time = "15:00"
    tz = "Asia/Kolkata"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$baseUrl/api/v1/finalize" -Method Post -ContentType "application/json" -Body $finalPayload | ConvertTo-Json

Write-Host "`n=== 8. End-to-End Pipeline (Clean Input) ===" -ForegroundColor Cyan
$e2ePayload = @{
    text = "Book dentist next Friday at 3pm"
    reference_date = "2025-09-19"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$baseUrl/api/v1/appointment?include_stages=true" -Method Post -ContentType "application/json" -Body $e2ePayload | ConvertTo-Json -Depth 5

Write-Host "`n=== 9. End-to-End Pipeline (Ambiguous Request - Guardrail) ===" -ForegroundColor Cyan
$guardPayload = @{
    text = "Book doctor appointment sometime next week"
    reference_date = "2025-09-19"
} | ConvertTo-Json
Invoke-RestMethod -Uri "$baseUrl/api/v1/appointment" -Method Post -ContentType "application/json" -Body $guardPayload | ConvertTo-Json
