# Dockerfile

# Verwende das neueste Python-Image
FROM python:3.12.4-slim

# Setze das Arbeitsverzeichnis
WORKDIR /app

# Kopiere die requirements.txt und installiere Abhängigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere den Rest des Codes
COPY . .

# Kopiere die description und prompt Ordner in den Container
COPY description /app/description
COPY prompt /app/prompt

# Erstelle einen Volumenpunkt für logs
VOLUME /app/logs

# Setze den Command für den Containerstart
CMD ["python", "JohnnyTheDiscordBot.py"]
