FROM python:3.13-slim

# System deps for OCR (Tesseract + poppler for pdf2image) — optional but enables real OCR.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr poppler-utils gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
