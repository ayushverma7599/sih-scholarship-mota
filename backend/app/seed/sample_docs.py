"""Generate synthetic sample document PDFs (with a 'SAMPLE' watermark) plus a
ground-truth sidecar (`<file>.truth.json`) so the OCR/extraction demo runs
end-to-end even without the Tesseract binary installed.

NOTHING here is a real government document — every page is watermarked SAMPLE.
"""
from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _watermark(c, w, h):
    c.saveState()
    c.setFont("Helvetica-Bold", 60)
    c.setFillColorRGB(0.92, 0.92, 0.92)
    c.translate(w / 2, h / 2)
    c.rotate(40)
    c.drawCentredString(0, 0, "SAMPLE")
    c.restoreState()


# Human-readable titles + which fields print on each doc type.
_DOC_TITLES = {
    "st_certificate": "SCHEDULED TRIBE (ST) CERTIFICATE",
    "income_certificate": "INCOME CERTIFICATE",
    "aadhaar": "AADHAAR (SAMPLE)",
    "marksheet": "MARKSHEET / GRADE CARD",
    "admission_letter": "ADMISSION / OFFER LETTER",
    "net_gate_scorecard": "NET / GATE SCORECARD",
    "research_proposal": "RESEARCH PROPOSAL",
}

_DOC_LINES = {
    "st_certificate": ["name", "dob", "certificate_number", "issuing_authority", "valid_upto"],
    "income_certificate": ["name", "income_amount", "certificate_number", "issuing_authority", "valid_upto"],
    "aadhaar": ["name", "dob", "aadhaar"],
    "marksheet": ["name", "marks", "certificate_number", "issuing_authority"],
    "admission_letter": ["name", "issuing_authority", "certificate_number"],
    "net_gate_scorecard": ["name", "marks", "certificate_number", "issuing_authority"],
    "research_proposal": ["name", "issuing_authority"],
}

_LABELS = {
    "name": "Name", "dob": "Date of Birth", "certificate_number": "Certificate No.",
    "issuing_authority": "Issued by", "valid_upto": "Valid Upto",
    "income_amount": "Annual Income", "aadhaar": "Aadhaar",
    "marks": "Marks/Percentage",
}


def generate_document(dest_dir: str, doc_type: str, fields: dict) -> str:
    """Write a watermarked sample PDF + a .truth.json sidecar. Returns the PDF path."""
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    stem = f"{doc_type}_{abs(hash(json.dumps(fields, sort_keys=True))) % 10_000_000}"
    pdf_path = str(Path(dest_dir) / f"{stem}.pdf")

    c = canvas.Canvas(pdf_path, pagesize=A4)
    w, h = A4
    _watermark(c, w, h)

    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(w / 2, h - 25 * mm, "Government of India (SAMPLE DOCUMENT)")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(w / 2, h - 33 * mm, _DOC_TITLES.get(doc_type, doc_type.upper()))
    c.line(25 * mm, h - 38 * mm, w - 25 * mm, h - 38 * mm)

    c.setFont("Helvetica", 11)
    y = h - 52 * mm
    for key in _DOC_LINES.get(doc_type, list(fields.keys())):
        if key in fields:
            label = _LABELS.get(key, key.replace("_", " ").title())
            val = fields[key]
            if key == "income_amount":
                val = f"Rs. {val}"
            c.drawString(30 * mm, y, f"{label}: {val}")
            y -= 9 * mm

    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(w / 2, 15 * mm,
                        "Synthetic sample for prototype demo only — not a real certificate.")
    c.showPage()
    c.save()

    # Sidecar with ground-truth values + declared doc type (drives the extractor).
    truth = dict(fields)
    truth["_doc_type"] = doc_type
    Path(f"{pdf_path}.truth.json").write_text(json.dumps(truth, indent=2))
    return pdf_path
