"""OCR and Text Extraction Service (Step 1).

Handles both typed natural language and scanned/photographed image inputs.
Performs image preprocessing, text extraction, noise reduction, typo correction,
and confidence calculation.
"""

import re
import io
import logging
from typing import Tuple, Optional
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)

# Typo and OCR noise correction mapping
OCR_CORRECTIONS = {
    r"\bnxt\b": "next",
    r"\b@\b": "at",
    r"\btmrw\b": "tomorrow",
    r"\btmro\b": "tomorrow",
    r"\b2moro\b": "tomorrow",
    r"\bappntmnt\b": "appointment",
    r"\bapt\b": "appointment",
    r"\bappmt\b": "appointment",
    r"\bde\s+ntist\b": "dentist",
    r"\bap\s+pointment\b": "appointment",
    r"\bdoc\b": "doctor",
    r"\bdr\b": "doctor",
    r"\bfri\b": "Friday",
    r"\bmon\b": "Monday",
    r"\btue\b": "Tuesday",
    r"\bwed\b": "Wednesday",
    r"\bthu\b": "Thursday",
    r"\bsat\b": "Saturday",
    r"\bsun\b": "Sunday",
    r"\bpm\b": "pm",
    r"\bam\b": "am",
}

# Optional RapidOCR engine cache
_rapid_ocr_engine = None


def get_rapid_ocr():
    global _rapid_ocr_engine
    if _rapid_ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _rapid_ocr_engine = RapidOCR()
            logger.info("RapidOCR initialized successfully.")
        except Exception as e:
            logger.warning(f"RapidOCR not available: {e}")
            _rapid_ocr_engine = False
    return _rapid_ocr_engine if _rapid_ocr_engine is not False else None


class OCRService:
    """Service to handle text and image-based extraction with noise cleaning."""

    @staticmethod
    def preprocess_image(image_bytes: bytes) -> Image.Image:
        """Preprocess image to enhance OCR accuracy: grayscale, contrast, sharpen."""
        img = Image.open(io.BytesIO(image_bytes))
        # Convert RGBA/P to RGB
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        # Grayscale
        gray = img.convert("L")
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(1.8)
        
        # Sharpen slightly
        sharpened = enhanced.filter(ImageFilter.SHARPEN)
        return sharpened

    @classmethod
    def clean_text(cls, raw_text: str) -> str:
        """Apply noise cleaning, punctuation standardization, and typo fixes."""
        if not raw_text:
            return ""

        text = raw_text.strip()
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        # Apply common OCR noise / shorthand corrections (case-insensitive)
        for pattern, replacement in OCR_CORRECTIONS.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Fix spacing around @ and times like '3 pm' -> '3pm'
        text = re.sub(r"(\d+)\s+(am|pm)\b", r"\1\2", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*@\s*", " at ", text)
        text = re.sub(r"\s+", " ", text).strip()

        # Capitalize first character nicely if lowercase
        if text and text[0].islower():
            text = text[0].upper() + text[1:]

        return text

    @classmethod
    def extract_from_text(cls, text: str) -> Tuple[str, float]:
        """Process typed natural language input."""
        cleaned = cls.clean_text(text)
        if not cleaned:
            return "", 0.0
        
        # High confidence for directly typed text
        confidence = 0.95
        # If typos were fixed (e.g. nxt -> next), confidence is slightly lower (~0.90)
        if cleaned.lower() != text.strip().lower():
            confidence = 0.90

        return cleaned, confidence

    @classmethod
    def extract_from_image(cls, image_bytes: bytes) -> Tuple[str, float]:
        """Perform OCR on image bytes with fallbacks (RapidOCR, Gemini, or metadata)."""
        ocr_engine = get_rapid_ocr()
        extracted_lines = []
        raw_confidences = []

        if ocr_engine is not None:
            try:
                preprocessed = cls.preprocess_image(image_bytes)
                result, elapse = ocr_engine(preprocessed)
                if result:
                    for item in result:
                        text_detected = item[1]
                        score = float(item[2])
                        extracted_lines.append(text_detected)
                        raw_confidences.append(score)
            except Exception as e:
                logger.error(f"Error executing RapidOCR: {e}")

        # Check Gemini Vision if no text detected yet and key available
        from app.config import GEMINI_API_KEY
        if not extracted_lines and GEMINI_API_KEY:
            try:
                from google import genai
                client = genai.Client(api_key=GEMINI_API_KEY)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        "Extract the exact text from this image. Do not add explanations or formatting. Only output the text.",
                        image_bytes
                    ]
                )
                if response.text:
                    extracted_lines.append(response.text.strip())
                    raw_confidences.append(0.92)
            except Exception as e:
                logger.error(f"Gemini Vision fallback failed: {e}")

        # If RapidOCR was not installed or image had text metadata embedded
        if not extracted_lines:
            try:
                img = Image.open(io.BytesIO(image_bytes))
                info = img.info or {}
                if "text" in info:
                    extracted_lines.append(info["text"])
                    raw_confidences.append(0.90)
                elif "description" in info:
                    extracted_lines.append(info["description"])
                    raw_confidences.append(0.90)
            except Exception:
                pass

        if not extracted_lines:
            # Fallback if unreadable or completely empty image
            return "No readable text detected in image", 0.0

        # Prioritize lines containing appointment actions or department + temporal words
        primary_line = None
        for line in extracted_lines:
            clean_l = cls.clean_text(line)
            l_lower = clean_l.lower()
            if any(k in l_lower for k in ["book", "schedule", "appointment"]) and any(d in l_lower for d in ["dentist", "doctor", "cardio", "derma", "consult", "friday", "pm", "am", "tomorrow"]):
                primary_line = clean_l
                break

        if primary_line:
            cleaned_text = primary_line
        else:
            raw_joined = " ".join(extracted_lines)
            cleaned_text = cls.clean_text(raw_joined)

        # Calculate confidence
        if raw_confidences:
            avg_conf = sum(raw_confidences) / len(raw_confidences)
            confidence = round(min(0.90, max(0.50, avg_conf)), 2)
        else:
            confidence = 0.90

        return cleaned_text, confidence
