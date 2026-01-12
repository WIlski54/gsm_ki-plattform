# Dockerfile für KI-Projektplattform
FROM python:3.11-slim

# Arbeitsverzeichnis
WORKDIR /app

# System-Abhängigkeiten
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python-Abhängigkeiten installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# App-Code kopieren
COPY . .

# Verzeichnisse erstellen
RUN mkdir -p /app/data /app/static/uploads

# Port freigeben
EXPOSE 5000

# Umgebungsvariablen
ENV FLASK_APP=app.py
ENV DATA_DIR=/app/data
ENV UPLOAD_FOLDER=/app/static/uploads

# Start mit Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
