"""Entity Extraction Service (Step 2).

Extracts date phrases, time phrases, and medical departments from raw text.
Supports both pattern-based NLP and LLM-assisted extraction.
"""

import re
import json
import logging
from typing import Tuple, Optional, Dict
from app.config import DEPARTMENT_TAXONOMY, GEMINI_API_KEY
from app.schemas import ExtractedEntities

logger = logging.getLogger(__name__)

# Common date phrase patterns
DATE_PATTERNS = [
    r"\b(next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
    r"\b(this\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
    r"\b(coming\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
    r"\b(tomorrow|tmrw|today|day\s+after\s+tomorrow)\b",
    r"\b(on\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?:\s+\d{4})?)\b",
    r"\b((?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?)\b",
    r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b",
    r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b",
    # Vague date patterns (for ambiguity detection)
    r"\b(sometime\s+next\s+week)\b",
    r"\b(next\s+week)\b",
    r"\b(this\s+week)\b",
    r"\b(sometime\s+soon)\b",
]

# Common time phrase patterns
TIME_PATTERNS = [
    r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b",
    r"\b(?:at\s+)?(\d{1,2}:\d{2})\b",
    r"\b(?:at\s+)?(\d{1,2}\s*(?:am|pm))\b",
    r"\b(morning|afternoon|evening|night)\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b",
    r"\b(noon|midnight)\b",
]


class EntityService:
    """Service to extract appointment scheduling entities from text."""

    @classmethod
    def extract_entities_regex(cls, raw_text: str) -> Tuple[ExtractedEntities, float]:
        """Fast, robust deterministic regex-based entity extraction."""
        lower_text = raw_text.lower()

        # 1. Extract Date Phrase
        date_phrase: Optional[str] = None
        for pattern in DATE_PATTERNS:
            match = re.search(pattern, raw_text, flags=re.IGNORECASE)
            if match:
                date_phrase = match.group(0).strip()
                # Clean leading 'on '
                if date_phrase.lower().startswith("on "):
                    date_phrase = date_phrase[3:].strip()
                break

        # 2. Extract Time Phrase
        time_phrase: Optional[str] = None
        for pattern in TIME_PATTERNS:
            match = re.search(pattern, raw_text, flags=re.IGNORECASE)
            if match:
                # If matched full group
                time_phrase = match.group(0).strip()
                # Clean leading 'at '
                if time_phrase.lower().startswith("at "):
                    time_phrase = time_phrase[3:].strip()
                break

        # 3. Extract Department
        department: Optional[str] = None
        # Check taxonomy keywords sorted by length descending so multi-word matches first
        sorted_dept_keys = sorted(DEPARTMENT_TAXONOMY.keys(), key=lambda k: len(k), reverse=True)
        for key in sorted_dept_keys:
            # Match whole word
            if re.search(r"\b" + re.escape(key) + r"\b", lower_text):
                department = key
                break

        # Calculate confidence
        detected_count = sum(1 for x in [date_phrase, time_phrase, department] if x)
        if detected_count == 3:
            confidence = 0.85
        elif detected_count == 2:
            confidence = 0.65
        elif detected_count == 1:
            confidence = 0.45
        else:
            confidence = 0.20

        return ExtractedEntities(
            date_phrase=date_phrase,
            time_phrase=time_phrase,
            department=department
        ), confidence

    @classmethod
    def extract_with_llm(cls, raw_text: str) -> Optional[Tuple[ExtractedEntities, float]]:
        """LLM-based extraction using Gemini if API key is provided."""
        if not GEMINI_API_KEY:
            return None

        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            prompt = f"""You are a clinical appointment entity extractor.
Extract the date phrase, time phrase, and medical department from this request:
"{raw_text}"

Return ONLY a JSON object with this exact structure:
{{
  "date_phrase": "<exact extracted date phrase or null>",
  "time_phrase": "<exact extracted time phrase or null>",
  "department": "<extracted department or specialist or null>",
  "confidence": <float between 0.7 and 0.95>
}}
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            data = json.loads(response.text)
            return ExtractedEntities(
                date_phrase=data.get("date_phrase"),
                time_phrase=data.get("time_phrase"),
                department=data.get("department")
            ), float(data.get("confidence", 0.85))
        except Exception as e:
            logger.warning(f"LLM entity extraction fallback to regex: {e}")
            return None

    @classmethod
    def extract(cls, raw_text: str) -> Tuple[ExtractedEntities, float]:
        """Extract entities using LLM if available, otherwise fast deterministic NLP."""
        # Try regex first
        entities, confidence = cls.extract_entities_regex(raw_text)
        
        # If all entities found cleanly, regex is ultra fast and reliable
        if entities.date_phrase and entities.time_phrase and entities.department:
            return entities, confidence

        # If partial or missing and Gemini key is present, try LLM
        llm_result = cls.extract_with_llm(raw_text)
        if llm_result:
            return llm_result

        return entities, confidence
