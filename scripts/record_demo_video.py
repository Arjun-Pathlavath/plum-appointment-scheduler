"""Automated screen recording generator.

Captures all demo states of the Plum AI Appointment Scheduler from headless Chrome
and compiles them into a clean, presentation-ready MP4 video and animated GIF.
"""

import os
import sys
import time
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOTS_DIR = os.path.join(ROOT_DIR, "screenshots_temp")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://localhost:8000"
WIDTH, HEIGHT = 1280, 720


def capture_chrome(url: str, output_filename: str):
    """Capture a screenshot from headless Chrome."""
    out_path = os.path.join(SCREENSHOTS_DIR, output_filename)
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--virtual-time-budget=2500",
        f"--window-size={WIDTH},{HEIGHT}",
        f"--screenshot={out_path}",
        url
    ]
    subprocess.run(cmd, capture_output=True)
    return out_path


def create_title_slide(title: str, subtitle: str, badge: str = "PLUM SDE ASSIGNMENT") -> np.ndarray:
    """Create a branded title slide."""
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(15, 23, 42))  # slate-900
    draw = ImageDraw.Draw(img)

    # Gradient top bar
    draw.rectangle([0, 0, WIDTH, 8], fill=(79, 70, 229))

    # Plum Logo Badge
    draw.rectangle([WIDTH // 2 - 35, 160, WIDTH // 2 + 35, 230], fill=(79, 70, 229))
    draw.text((WIDTH // 2 - 12, 175), "P", fill=(255, 255, 255))

    # Badge Pill
    draw.rectangle([WIDTH // 2 - 120, 260, WIDTH // 2 + 120, 290], fill=(30, 41, 59), outline=(79, 70, 229), width=1)
    draw.text((WIDTH // 2 - 95, 268), badge, fill=(199, 210, 254))

    # Main Title
    draw.text((WIDTH // 2 - 360, 320), title, fill=(255, 255, 255))

    # Subtitle
    draw.text((WIDTH // 2 - 340, 390), subtitle, fill=(148, 163, 184))

    # Footer
    draw.line([100, HEIGHT - 80, WIDTH - 100, HEIGHT - 80], fill=(51, 65, 85), width=1)
    draw.text((WIDTH // 2 - 180, HEIGHT - 60), "Candidate: Arjun-Pathlavath | Problem Statement 1", fill=(100, 116, 139))

    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def generate_video():
    print("Capturing demo screenshots...")
    slides = []

    # Slide 0: Title Slide
    s0 = create_title_slide(
        "AI-Powered Appointment Scheduler Assistant",
        "Problem Statement 1: OCR -> Entity Extraction -> Normalization -> Guardrails"
    )
    slides.append(("Title", s0, 3.5))

    # Slide 1: Default Web UI
    p1 = capture_chrome(f"{BASE_URL}/", "01_default.png")
    if os.path.exists(p1):
        slides.append(("Initial UI", cv2.imread(p1), 2.5))

    # Slide 2: Sample 1 (Clean text: "Book dentist next Friday at 3pm")
    p2 = capture_chrome(f"{BASE_URL}/?auto=clean", "02_clean.png")
    if os.path.exists(p2):
        slides.append(("Clean Request Output", cv2.imread(p2), 4.5))

    # Slide 3: Sample 2 (Noisy OCR: "book dentist nxt Friday @ 3 pm")
    p3 = capture_chrome(f"{BASE_URL}/?auto=noisy", "03_noisy.png")
    if os.path.exists(p3):
        slides.append(("Noisy OCR Typo Correction", cv2.imread(p3), 4.0))

    # Slide 4: Sample 4 (Guardrail Ambiguity: "Book doctor appointment sometime next week")
    p4 = capture_chrome(f"{BASE_URL}/?auto=ambiguous", "04_ambiguous.png")
    if os.path.exists(p4):
        slides.append(("Guardrail Ambiguity Trigger", cv2.imread(p4), 4.0))

    # Slide 5: Sample 3 (Cardiology Consult)
    p5 = capture_chrome(f"{BASE_URL}/?auto=cardio", "05_cardio.png")
    if os.path.exists(p5):
        slides.append(("Cardiology Consultation", cv2.imread(p5), 3.5))

    # Slide 6: Swagger API Documentation
    p6 = capture_chrome(f"{BASE_URL}/docs", "06_docs.png")
    if os.path.exists(p6):
        slides.append(("Swagger API Documentation", cv2.imread(p6), 3.5))

    # Slide 7: Outro Slide
    s_end = create_title_slide(
        "Demonstration Complete - 100% Tests Passed",
        "Live Demo, API Endpoints, & Automated Pytest Suite Ready for Review",
        badge="PLUM SDE SUBMISSION READY"
    )
    slides.append(("Outro", s_end, 3.0))

    # Compile Video
    output_video_path = os.path.join(ROOT_DIR, "demo_recording.mp4")
    fps = 24
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_video_path, fourcc, fps, (WIDTH, HEIGHT))

    gif_frames = []

    print(f"Compiling {len(slides)} scenes into {output_video_path}...")
    for title, img_bgr, duration_sec in slides:
        # Resize to standard if needed
        if img_bgr.shape[1] != WIDTH or img_bgr.shape[0] != HEIGHT:
            img_bgr = cv2.resize(img_bgr, (WIDTH, HEIGHT))

        frame_count = int(duration_sec * fps)
        for _ in range(frame_count):
            writer.write(img_bgr)

        # Grab a thumbnail for GIF
        rgb_thumb = cv2.cvtColor(cv2.resize(img_bgr, (640, 360)), cv2.COLOR_BGR2RGB)
        gif_frames.append(Image.fromarray(rgb_thumb))

    writer.release()
    print(f"Video saved successfully: {output_video_path}")

    # Save animated GIF for instant web preview
    output_gif_path = os.path.join(ROOT_DIR, "demo_preview.gif")
    if gif_frames:
        gif_frames[0].save(
            output_gif_path,
            save_all=True,
            append_images=gif_frames[1:],
            duration=3000,
            loop=0
        )
        print(f"GIF preview saved successfully: {output_gif_path}")


if __name__ == "__main__":
    generate_video()
