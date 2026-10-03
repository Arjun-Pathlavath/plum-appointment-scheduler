"""Application configuration and department taxonomy settings."""

import os
from typing import Dict

# Application Settings
APP_NAME = "Plum AI-Powered Appointment Scheduler"
APP_VERSION = "1.0.0"
DEFAULT_TIMEZONE = "Asia/Kolkata"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# AI Provider Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Standardized Clinical Department Taxonomy Mapping
DEPARTMENT_TAXONOMY: Dict[str, str] = {
    # Dental
    "dentist": "Dentistry",
    "dental": "Dentistry",
    "dentistry": "Dentistry",
    "teeth": "Dentistry",
    "tooth": "Dentistry",
    "orthodontist": "Dentistry",

    # General & Family Medicine
    "physician": "General Medicine",
    "doctor": "General Medicine",
    "gp": "General Medicine",
    "general physician": "General Medicine",
    "general medicine": "General Medicine",
    "family doctor": "General Medicine",
    "consultation": "General Medicine",
    "checkup": "General Medicine",

    # Cardiology
    "cardiologist": "Cardiology",
    "cardio": "Cardiology",
    "cardiology": "Cardiology",
    "heart": "Cardiology",

    # Dermatology
    "dermatologist": "Dermatology",
    "derma": "Dermatology",
    "dermatology": "Dermatology",
    "skin": "Dermatology",

    # Ophthalmology
    "ophthalmologist": "Ophthalmology",
    "eye": "Ophthalmology",
    "eyes": "Ophthalmology",
    "eye doctor": "Ophthalmology",
    "optometrist": "Ophthalmology",
    "ophthalmology": "Ophthalmology",

    # Orthopedics
    "orthopedic": "Orthopedics",
    "orthopedist": "Orthopedics",
    "ortho": "Orthopedics",
    "orthopedics": "Orthopedics",
    "bone": "Orthopedics",
    "joint": "Orthopedics",

    # Pediatrics
    "pediatrician": "Pediatrics",
    "pediatrics": "Pediatrics",
    "child doctor": "Pediatrics",
    "kid doctor": "Pediatrics",

    # ENT
    "ent": "ENT (Otolaryngology)",
    "ear": "ENT (Otolaryngology)",
    "nose": "ENT (Otolaryngology)",
    "throat": "ENT (Otolaryngology)",
    "otolaryngologist": "ENT (Otolaryngology)",

    # Gynecology
    "gynecologist": "Gynecology",
    "gyno": "Gynecology",
    "gynecology": "Gynecology",
    "obgyn": "Gynecology",

    # Neurology
    "neurologist": "Neurology",
    "neuro": "Neurology",
    "neurology": "Neurology",
    "brain": "Neurology",

    # Psychiatry / Mental Health
    "psychiatrist": "Psychiatry",
    "psychologist": "Psychiatry",
    "therapy": "Psychiatry",
    "mental health": "Psychiatry",
}
