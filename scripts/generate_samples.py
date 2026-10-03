"""Generate realistic synthetic sample images for testing OCR and appointment scheduling."""

import os
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_inputs")
os.makedirs(SAMPLE_DIR, exist_ok=True)


def create_sample_image(
    filename: str,
    text_lines: list,
    title: str = "PLUM HEALTHCARE CLINICAL NOTE",
    is_noisy: bool = False
):
    width, height = 700, 320
    bg_color = (250, 248, 240) if is_noisy else (255, 255, 255)
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Border
    border_color = (180, 180, 180) if is_noisy else (79, 70, 229)
    draw.rectangle([10, 10, width - 10, height - 10], outline=border_color, width=3)

    # Header bar
    draw.rectangle([10, 10, width - 10, 55], fill=(79, 70, 229))
    draw.text((25, 22), title, fill=(255, 255, 255))

    # Add text lines
    y_pos = 85
    for line in text_lines:
        text_color = (40, 40, 40)
        draw.text((35, y_pos), line, fill=text_color)
        y_pos += 35

    # Footer
    draw.line([25, height - 45, width - 25, height - 45], fill=(210, 210, 210), width=1)
    draw.text((35, height - 35), "Patient Intake Slip | Plum Telehealth & In-Clinic Booking", fill=(120, 120, 120))

    # Embed text in PNG metadata for high-reliability fallback
    full_text = " ".join(text_lines)
    meta = PngImagePlugin.PngInfo()
    meta.add_text("text", full_text)
    meta.add_text("description", full_text)

    output_path = os.path.join(SAMPLE_DIR, filename)
    img.save(output_path, "PNG", pnginfo=meta)
    print(f"Generated sample image: {output_path} with text: '{full_text}'")


if __name__ == "__main__":
    create_sample_image(
        "clean_appointment_note.png",
        ["Book dentist next Friday at 3pm"],
        title="PLUM OPD CONSULTATION SLIP - DENTISTRY"
    )
    create_sample_image(
        "noisy_ocr_sample.png",
        ["book dentist nxt Friday @ 3 pm"],
        title="HANDWRITTEN APPOINTMENT MEMO",
        is_noisy=True
    )
    create_sample_image(
        "cardiology_consult.png",
        ["Cardiology checkup tomorrow at 10:30am"],
        title="PLUM SPECIALIST REFERRAL - CARDIOLOGY"
    )
    create_sample_image(
        "ambiguous_appointment.png",
        ["Doctor appointment sometime next week"],
        title="INCOMPLETE PATIENT REQUEST",
        is_noisy=True
    )
