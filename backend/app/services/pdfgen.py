"""PDF generation for selection / sanction letters using reportlab.

Returns raw PDF bytes so the API can stream them without touching disk.
"""
from __future__ import annotations

import io
from datetime import date


def selection_letter(
    *,
    applicant_name: str,
    scheme_name: str,
    scheme_code: str,
    academic_year: str,
    rank: int | None,
    reference_no: str,
) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Header
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(w / 2, h - 30 * mm, "Government of India")
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(w / 2, h - 38 * mm, "Ministry of Tribal Affairs")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 45 * mm, f"{scheme_name} ({scheme_code})")

    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.line(25 * mm, h - 50 * mm, w - 25 * mm, h - 50 * mm)

    # Meta
    c.setFont("Helvetica", 10)
    c.drawString(25 * mm, h - 60 * mm, f"Ref. No.: {reference_no}")
    c.drawRightString(w - 25 * mm, h - 60 * mm, f"Date: {date.today().isoformat()}")

    # Body
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(w / 2, h - 72 * mm, "PROVISIONAL SELECTION LETTER")

    body = [
        f"Dear {applicant_name},",
        "",
        f"We are pleased to inform you that you have been provisionally selected under",
        f"the {scheme_name} ({scheme_code}) for the academic year {academic_year},",
        (f"with a merit rank of {rank}." if rank else "based on the published merit list."),
        "",
        "This selection is subject to final verification of your documents and",
        "fulfilment of all scheme conditions as per the official MoTA guidelines.",
        "",
        "You are requested to submit your joining report through the portal within the",
        "stipulated period to activate your fellowship/scholarship.",
        "",
        "Warm regards,",
        "Selection Committee",
        "Ministry of Tribal Affairs",
    ]
    y = h - 84 * mm
    c.setFont("Helvetica", 11)
    for line in body:
        c.drawString(25 * mm, y, line)
        y -= 7 * mm

    # Watermark: prototype notice
    c.saveState()
    c.setFont("Helvetica-Bold", 40)
    c.setFillColorRGB(0.9, 0.9, 0.9)
    c.translate(w / 2, h / 2)
    c.rotate(35)
    c.drawCentredString(0, 0, "PROTOTYPE — SAMPLE")
    c.restoreState()

    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(
        w / 2, 15 * mm,
        "System-generated prototype document — not an official Government of India letter.",
    )
    c.showPage()
    c.save()
    return buf.getvalue()
