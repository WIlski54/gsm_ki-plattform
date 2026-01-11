# KI-Projektplattform 🚀

Eine elegante Austauschplattform für KI-gestützte Unterrichtsprojekte.

## Features

- 🎨 **Modernes Design** mit Tailwind CSS und Alpine.js
- 📁 **Fachbereich-Kategorien** für übersichtliche Organisation
- 🔍 **Suchfunktion** über Titel, Beschreibung und Tags
- 📤 **Upload-System** für Projektdateien
- 📊 **Download-Tracking** und Statistiken
- 📱 **Responsive Design** für alle Geräte

## Tech Stack

- **Backend:** Flask (Python)
- **Frontend:** Tailwind CSS, Alpine.js, Lucide Icons
- **Storage:** JSON-basiert (später erweiterbar auf GitHub/Supabase)

## Lokale Entwicklung

```bash
# Repository klonen
git clone https://github.com/DEIN-USERNAME/ki-plattform.git
cd ki-plattform

# Virtual Environment erstellen
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Dependencies installieren
pip install -r requirements.txt

# App starten
python app.py
```

Die App läuft dann unter `http://localhost:5000`

## Deployment auf Render.com

### 1. GitHub Repository erstellen

1. Neues Repository auf GitHub erstellen
2. Code pushen:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/DEIN-USERNAME/ki-plattform.git
   git push -u origin main
   ```

### 2. Render.com Setup

1. Account auf [render.com](https://render.com) erstellen
2. **New > Web Service** wählen
3. GitHub Repository verbinden
4. Einstellungen:
   - **Name:** ki-plattform (oder beliebig)
   - **Region:** Frankfurt (EU)
   - **Branch:** main
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`

5. Environment Variables hinzufügen:
   - `SECRET_KEY`: Ein sicherer zufälliger String
   - `PYTHON_VERSION`: 3.11.0

6. **Create Web Service** klicken

### 3. Persistente Datenspeicherung (Optional)

Da Render's Filesystem ephemeral ist, gibt es mehrere Optionen:

#### Option A: GitHub als Storage
- Projekte werden als JSON im Repository gespeichert
- Änderungen via GitHub API committen

#### Option B: Render Disk (kostenpflichtig)
- Persistent Disk zum Service hinzufügen
- Dateien bleiben zwischen Deploys erhalten

#### Option C: Supabase Storage (empfohlen)
- Gratis-Tier mit 1GB Storage
- Einfache REST API

## Projektstruktur

```
ki-plattform/
├── app.py              # Flask-Anwendung
├── requirements.txt    # Python-Dependencies
├── projects.json       # Projektdaten (generiert)
├── static/
│   └── uploads/        # Hochgeladene Dateien
└── templates/
    ├── base.html       # Basis-Template
    ├── index.html      # Startseite
    ├── category.html   # Kategorieansicht
    ├── project.html    # Projektdetails
    ├── upload.html     # Upload-Formular
    ├── search.html     # Suchergebnisse
    └── error.html      # Fehlerseite
```

## Anpassung

### Kategorien bearbeiten

Die Fachbereiche können in `app.py` im `CATEGORIES` Dictionary angepasst werden:

```python
CATEGORIES = {
    'neue-kategorie': {
        'name': 'Neue Kategorie',
        'icon': '🆕',
        'description': 'Beschreibung',
        'color': 'blue',  # Tailwind-Farbe
        'subcategories': ['Sub1', 'Sub2']
    }
}
```

### Design anpassen

- **Farben:** In `base.html` unter `tailwind.config`
- **Schriften:** Google Fonts Import in `base.html`
- **Styling:** Tailwind-Klassen in den Templates

## Nächste Schritte

- [ ] Authentifizierung für Upload
- [ ] GitHub API Integration für persistente Speicherung
- [ ] Projekt-Vorschau (HTML-Dateien inline anzeigen)
- [ ] Bewertungs-/Kommentarsystem
- [ ] Admin-Dashboard

## Lizenz

MIT License - Frei verwendbar für Schulen und Bildungseinrichtungen.

---

Made with ❤️ für Lehrer:innen
