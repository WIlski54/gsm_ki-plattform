import os
import json
import datetime
import shutil
import math
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, abort
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# ------------------------------------------------------------------------------
# 1. KONFIGURATION & SETUP
# ------------------------------------------------------------------------------

app = Flask(__name__)
# ACHTUNG: Ändere diesen Schlüssel für die Produktion!
app.secret_key = "DEIN_GEHEIMER_SCHLUESSEL_HIER_AENDERN"

# Pfade für Persistenz (Docker Volumes)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

# Sicherstellen, dass Verzeichnisse existieren
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Max 50 MB Upload

# Erlaubte Dateiendungen
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'mp3', 'mp4', 'zip', 'html', 'htm'}

# Dateinamen für JSON-Datenbanken
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
PROJECTS_FILE = os.path.join(DATA_DIR, 'projects.json')
ACTIVITY_FILE = os.path.join(DATA_DIR, 'activity.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')

# ------------------------------------------------------------------------------
# 2. KONSTANTEN & DATENSTRUKTUREN
# ------------------------------------------------------------------------------

CATEGORIES = {
    'naturwissenschaften': {'name': 'Naturwissenschaften', 'icon': '🔬', 'color': 'emerald'},
    'sprachen': {'name': 'Sprachen', 'icon': '📚', 'color': 'blue'},
    'gesellschaft': {'name': 'Gesellschaftswissenschaften', 'icon': '🌍', 'color': 'amber'},
    'mathe_info': {'name': 'Mathematik & Informatik', 'icon': '📐', 'color': 'indigo'},
    'kunst_musik': {'name': 'Kunst & Musik', 'icon': '🎨', 'color': 'pink'},
    'faecheruebergreifend': {'name': 'Fächerübergreifend', 'icon': '✨', 'color': 'violet'}
}

MATERIAL_TYPES = [
    {'id': 'worksheet_analog', 'name': 'Arbeitsblatt (analog)', 'icon': '📄'},
    {'id': 'worksheet_digital', 'name': 'Arbeitsblatt (interaktiv)', 'icon': '🎮'},
    {'id': 'worksheet_ai', 'name': 'Arbeitsblatt (KI)', 'icon': '🤖'},
    {'id': 'presentation', 'name': 'Präsentation', 'icon': '📊'},
    {'id': 'video', 'name': 'Erklärvideo', 'icon': '🎬'},
    {'id': 'audio', 'name': 'Audio/Podcast', 'icon': '🎧'},
    {'id': 'other', 'name': 'Sonstiges', 'icon': '📦'}
]

DEFAULT_SETTINGS = {
    'download_cost': 1,
    'upload_reward': 3,
    'start_tokens': 3
}

# Globale Variablen für Daten (werden beim Start geladen)
users = {}
projects = []
activity_log = []
system_settings = {}

# ------------------------------------------------------------------------------
# 3. HILFSFUNKTIONEN (DATENBANK & LOGIK)
# ------------------------------------------------------------------------------

def load_data():
    """Lädt alle Daten aus den JSON-Dateien."""
    global users, projects, activity_log, system_settings
    
    # User laden
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
        except Exception as e:
            print(f"Fehler beim Laden der User: {e}")
            users = {}
    
    # Falls keine User existieren -> Standard-Admin erstellen
    if not users:
        users = {
            "Administrator": {
                "password": generate_password_hash("admin123"),
                "tokens": 9999,
                "is_admin": True,
                "can_upload": True, # Admin darf immer
                "downloads": []
            }
        }
        save_data()

    # Projekte laden
    if os.path.exists(PROJECTS_FILE):
        try:
            with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
                projects = json.load(f)
        except Exception as e:
            print(f"Fehler beim Laden der Projekte: {e}")
            projects = []
    
    # Aktivitäten laden
    if os.path.exists(ACTIVITY_FILE):
        try:
            with open(ACTIVITY_FILE, 'r', encoding='utf-8') as f:
                activity_log = json.load(f)
        except Exception as e:
            print(f"Fehler beim Laden der Aktivitäten: {e}")
            activity_log = []

    # Einstellungen laden
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                system_settings = json.load(f)
        except Exception as e:
            print(f"Fehler beim Laden der Settings: {e}")
            system_settings = DEFAULT_SETTINGS.copy()
    else:
        system_settings = DEFAULT_SETTINGS.copy()
        save_settings()

def save_data():
    """Speichert User und Projekte in JSON-Dateien."""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4)
        with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(projects, f, indent=4)
    except Exception as e:
        print(f"Fehler beim Speichern der Daten: {e}")

def save_activity():
    """Speichert das Aktivitätslog."""
    try:
        with open(ACTIVITY_FILE, 'w', encoding='utf-8') as f:
            json.dump(activity_log, f, indent=4)
    except Exception as e:
        print(f"Fehler beim Speichern der Aktivitäten: {e}")

def save_settings():
    """Speichert die Systemeinstellungen."""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(system_settings, f, indent=4)
    except Exception as e:
        print(f"Fehler beim Speichern der Settings: {e}")

def log_activity(user, action, details):
    """Schreibt einen Eintrag ins Logbuch."""
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "user": user,
        "action": action,
        "details": details
    }
    activity_log.insert(0, entry) # Neuester Eintrag oben
    if len(activity_log) > 200: # Log begrenzen auf 200 Einträge
        activity_log.pop()
    save_activity()

def allowed_file(filename):
    """Prüft die Dateiendung."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_icon(filename):
    """Gibt ein passendes Emoji für den Dateityp zurück."""
    if not filename: return '📄'
    ext = filename.rsplit('.', 1)[1].lower()
    icons = {
        'pdf': '📕', 'doc': '📘', 'docx': '📘',
        'xls': '📗', 'xlsx': '📗', 'ppt': '📙', 'pptx': '📙',
        'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️',
        'mp3': '🎧', 'wav': '🎧', 'mp4': '🎬', 'mov': '🎬',
        'zip': '📦', 'rar': '📦', 'html': '🌐', 'htm': '🌐'
    }
    return icons.get(ext, '📄')

# Beim Start einmal laden
load_data()

# ------------------------------------------------------------------------------
# 4. SICHERHEITS-CHECKS & CONTEXT
# ------------------------------------------------------------------------------

# NEU: Diese Funktion verhindert den "Ups!" 500 Fehler
@app.before_request
def check_user_validity():
    """Prüft vor JEDER Anfrage, ob der User in der Session noch existiert."""
    if 'user' in session and session['user'] not in users:
        # User ist in Session (Cookie), aber nicht in DB -> Logout erzwingen
        session.pop('user', None)
        return redirect(url_for('login'))

@app.context_processor
def inject_global_vars():
    """Stellt Variablen global in allen Templates zur Verfügung."""
    user_data = None
    is_admin = False
    can_upload = False
    user_tokens = 0
    
    if 'user' in session:
        user_data = users.get(session['user'])
        if user_data:
            user_tokens = user_data.get('tokens', 0)
            is_admin = user_data.get('is_admin', False)
            # Admin darf immer, User nur wenn Flag 'can_upload' True ist
            can_upload = is_admin or user_data.get('can_upload', False)

    return {
        'users': users,
        'projects': projects,
        'categories': CATEGORIES,
        'material_types': MATERIAL_TYPES,
        'user_tokens': user_tokens,
        'is_admin': is_admin,
        'can_upload': can_upload,
        'token_settings': system_settings,
        'get_file_icon': get_file_icon
    }

# ------------------------------------------------------------------------------
# 5. AUTH ROUTES (LOGIN / REGISTER / LOGOUT)
# ------------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = users.get(username)
        if user and check_password_hash(user['password'], password):
            session['user'] = username
            log_activity(username, "Login", "Erfolgreich angemeldet")
            return redirect(url_for('index'))
        
        flash("Ungültiger Benutzername oder Passwort", "error")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users:
            flash("Benutzername bereits vergeben", "error")
        elif len(password) < 4:
            flash("Passwort muss mindestens 4 Zeichen lang sein", "error")
        else:
            # Neuer User: Standard-Tokens, kein Admin, Standardmäßig KEIN Upload-Recht
            users[username] = {
                "password": generate_password_hash(password),
                "tokens": system_settings.get('start_tokens', 3),
                "is_admin": False,
                "can_upload": False, # Sicherheit: Erstmal verbieten
                "downloads": []
            }
            save_data()
            log_activity(username, "Registrierung", "Neuer Benutzer registriert")
            flash("Registrierung erfolgreich! Bitte einloggen.", "success")
            return redirect(url_for('login'))
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    if 'user' in session:
        log_activity(session['user'], "Logout", "Abgemeldet")
        session.pop('user', None)
    return redirect(url_for('login'))

# ------------------------------------------------------------------------------
# 6. MAIN ROUTES (USER BEREICH)
# ------------------------------------------------------------------------------

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Neueste Projekte für Dashboard filtern (letzte 6)
    sorted_projects = sorted(projects, key=lambda x: x['created'], reverse=True)
    recent_projects = sorted_projects[:6]
    
    # Beliebte Projekte (nach Downloads)
    popular_projects = sorted(projects, key=lambda x: x.get('downloads', 0), reverse=True)[:3]
    
    return render_template('index.html', recent_projects=recent_projects, popular_projects=popular_projects)

@app.route('/category/<category_id>')
def category(category_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if category_id not in CATEGORIES:
        return redirect(url_for('index'))
        
    # Projekte der Kategorie filtern
    cat_projects = [p for p in projects if p['category'] == category_id]
    
    # Sortierung anwenden
    sort_by = request.args.get('sort', 'newest')
    if sort_by == 'oldest':
        cat_projects.sort(key=lambda x: x['created'])
    elif sort_by == 'downloads':
        cat_projects.sort(key=lambda x: x.get('downloads', 0), reverse=True)
    else: # newest (default)
        cat_projects.sort(key=lambda x: x['created'], reverse=True)
        
    return render_template('category.html', category=CATEGORIES[category_id], projects=cat_projects, current_sort=sort_by)

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    project = next((p for p in projects if p['id'] == project_id), None)
    if not project:
        flash("Projekt nicht gefunden", "error")
        return redirect(url_for('index'))
        
    # Sicherer Zugriff auf User
    current_user = users.get(session['user'])
    if not current_user:
        return redirect(url_for('logout')) # Sollte dank before_request nicht passieren

    # Prüfen ob User Autor ist oder schon gekauft hat
    is_owner = project['author'] == session['user']
    is_admin = current_user.get('is_admin', False)
    
    # Hat der User das Projekt schon? (Download-Liste prüfen)
    has_purchased = project_id in current_user.get('downloads', []) or is_owner or is_admin
    
    # Download-Kosten berechnen
    cost = system_settings.get('download_cost', 1)
    if project.get('material_type') == 'worksheet_ai':
        cost = 3 
        
    can_user_download = current_user.get('tokens', 0) >= cost
    
    return render_template('project.html', 
                         project=project, 
                         is_owner=is_owner,
                         has_purchased=has_purchased,
                         can_user_download=can_user_download)

@app.route('/search')
def search():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    query = request.args.get('q', '').lower()
    if not query:
        return redirect(url_for('index'))
        
    results = [
        p for p in projects 
        if query in p['title'].lower() 
        or query in p.get('description', '').lower()
        or query in p.get('author', '').lower()
        or any(query in tag.lower() for tag in p.get('tags', []))
    ]
    
    return render_template('search_results.html', query=query, projects=results)

# ------------------------------------------------------------------------------
# 7. UPLOAD & DOWNLOAD LOGIK (MIT SICHERHEITS-CHECKS)
# ------------------------------------------------------------------------------

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user' not in session:
        return redirect(url_for('login'))

    # --- BERECHTIGUNGS-PRÜFUNG (SICHER) ---
    current_user = users.get(session['user'])
    if not current_user:
        return redirect(url_for('logout'))

    is_admin = current_user.get('is_admin', False)
    can_upload = current_user.get('can_upload', False)
    
    if not is_admin and not can_upload:
        flash("Keine Berechtigung: Uploads sind derzeit nur für freigeschaltete Kollegen möglich.", "error")
        return redirect(url_for('index'))
    # --- ENDE PRÜFUNG ---

    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        material_type = request.form['material_type']
        description = request.form.get('description', '')
        tags = [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()]
        project_url = request.form.get('project_url', '').strip()
        
        file = request.files['file']
        filename = None
        
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(original_filename)
            filename = f"{name}_{timestamp}{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # Neues Projekt anlegen
        new_id = 1 if not projects else max(p['id'] for p in projects) + 1
        new_project = {
            'id': new_id,
            'title': title,
            'category': category,
            'material_type': material_type,
            'description': description,
            'author': session['user'],
            'created': datetime.datetime.now().isoformat(),
            'downloads': 0,
            'filename': filename,
            'project_url': project_url if project_url else None,
            'tags': tags
        }
        
        projects.append(new_project)
        
        # Belohnung für Uploader
        reward = system_settings.get('upload_reward', 3)
        current_user['tokens'] += reward
        
        save_data()
        log_activity(session['user'], "Upload", f"Projekt '{title}' hochgeladen (+{reward} Tokens)")
        
        flash(f"Projekt erfolgreich hochgeladen! Du hast {reward} Tokens verdient.", "success")
        return redirect(url_for('project_detail', project_id=new_id))
        
    return render_template('upload.html')

@app.route('/download/<int:project_id>')
def download_file(project_id):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    project = next((p for p in projects if p['id'] == project_id), None)
    if not project or not project['filename']:
        flash("Datei nicht verfügbar", "error")
        return redirect(url_for('project_detail', project_id=project_id))
        
    user = users.get(session['user'])
    if not user:
        return redirect(url_for('logout'))
    
    is_owner = project['author'] == session['user']
    has_purchased = project_id in user.get('downloads', [])
    is_admin = user.get('is_admin', False)
    
    cost = system_settings.get('download_cost', 1)
    if project.get('material_type') == 'worksheet_ai':
        cost = 3
        
    if not is_owner and not has_purchased and not is_admin:
        if user['tokens'] < cost:
            flash("Nicht genügend Tokens!", "error")
            return redirect(url_for('project_detail', project_id=project_id))
            
        user['tokens'] -= cost
        user.setdefault('downloads', []).append(project_id)
        project['downloads'] = project.get('downloads', 0) + 1
        
        save_data()
        log_activity(session['user'], "Download", f"Projekt '{project['title']}' heruntergeladen (-{cost} Tokens)")
        flash(f"Download gestartet! {cost} Tokens abgezogen.", "success")
    
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], project['filename'], as_attachment=True)
    except FileNotFoundError:
        flash("Datei wurde auf dem Server nicht gefunden.", "error")
        return redirect(url_for('project_detail', project_id=project_id))

# ------------------------------------------------------------------------------
# 8. PREVIEW ROUTES (SICHERHEIT FÜR IFRAMES)
# ------------------------------------------------------------------------------

@app.route('/view/<filename>')
def view_file(filename):
    """Zeigt eine Datei (HTML) im Browser an."""
    if 'user' not in session:
        flash("Bitte erst einloggen.", "error")
        return redirect(url_for('login'))
    
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        return "Datei nicht gefunden", 404

@app.route('/serve_upload/<filename>')
def serve_upload(filename):
    """Hilfsroute für PDF.js und Bilder-Vorschau."""
    if 'user' not in session:
        abort(403)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ------------------------------------------------------------------------------
# 9. ADMIN BEREICH
# ------------------------------------------------------------------------------

@app.route('/admin')
def admin_dashboard():
    # Sicherer Check
    if 'user' not in session:
        return redirect(url_for('index'))
    
    user = users.get(session['user'])
    if not user or not user.get('is_admin'):
        return redirect(url_for('index'))
        
    # Statistiken berechnen
    total_projects = len(projects)
    total_users = len(users)
    total_downloads = sum(p.get('downloads', 0) for p in projects)
    total_tokens = sum(u.get('tokens', 0) for u in users.values())
    
    # Downloads nach Kategorie
    downloads_by_cat = {}
    for cat_id, cat_data in CATEGORIES.items():
        count = sum(p.get('downloads', 0) for p in projects if p['category'] == cat_id)
        downloads_by_cat[cat_id] = {
            'name': cat_data['name'],
            'icon': cat_data['icon'],
            'downloads': count
        }
        
    # Top 5 Projekte
    top_projects = sorted(projects, key=lambda x: x.get('downloads', 0), reverse=True)[:5]
        
    return render_template('admin/dashboard.html',
                         total_projects=total_projects,
                         total_users=total_users,
                         total_downloads=total_downloads,
                         total_tokens=total_tokens,
                         downloads_by_cat=downloads_by_cat,
                         top_projects=top_projects,
                         recent_activity=activity_log[:10])

@app.route('/admin/projects')
def admin_projects():
    if 'user' not in session or not users.get(session['user'], {}).get('is_admin'):
        return redirect(url_for('index'))
    return render_template('admin/projects.html', projects=projects)

@app.route('/admin/users')
def admin_users():
    # HIER LAG DER FEHLER 500: users[session['user']] stürzt ab, wenn User fehlt.
    # Jetzt sicher mit .get():
    if 'user' not in session or not users.get(session['user'], {}).get('is_admin'):
        return redirect(url_for('index'))
    return render_template('admin/users.html', users=users)

@app.route('/admin/activity')
def admin_activity():
    if 'user' not in session or not users.get(session['user'], {}).get('is_admin'):
        return redirect(url_for('index'))
    return render_template('admin/activity.html', activity_log=activity_log)

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if 'user' not in session or not users.get(session['user'], {}).get('is_admin'):
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        try:
            system_settings['download_cost'] = int(request.form['download_cost'])
            system_settings['upload_reward'] = int(request.form['upload_reward'])
            system_settings['start_tokens'] = int(request.form['start_tokens'])
            save_settings()
            flash("Einstellungen gespeichert!", "success")
        except ValueError:
            flash("Bitte gültige Zahlen eingeben.", "error")
            
    return render_template('admin/settings.html', settings=system_settings)

@app.route('/admin/delete_project/<int:project_id>', methods=['POST'])
def admin_delete_project(project_id):
    if 'user' not in session or not users.get(session['user'], {}).get('is_admin'):
        return redirect(url_for('index'))
        
    project = next((p for p in projects if p['id'] == project_id), None)
    if project:
        if project['filename']:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], project['filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
        
        projects.remove(project)
        save_data()
        log_activity(session['user'], "Admin", f"Projekt {project_id} gelöscht")
        flash("Projekt gelöscht.", "success")
        
    return redirect(url_for('admin_projects'))

@app.route('/admin/delete_user/<username>', methods=['POST'])
def admin_delete_user(username):
    if 'user' not in session or not users.get(session['user'], {}).get('is_admin'):
        return redirect(url_for('index'))
        
    if username in users:
        if users[username].get('is_admin'):
            flash("Administratoren können nicht gelöscht werden.", "error")
        else:
            del users[username]
            save_data()
            log_activity(session['user'], "Admin", f"User {username} gelöscht")
            flash(f"Benutzer {username} gelöscht.", "success")
            
    return redirect(url_for('admin_users'))

@app.route('/admin/users/toggle_upload/<username>', methods=['POST'])
def admin_toggle_upload(username):
    if 'user' not in session or not users.get(session['user'], {}).get('is_admin'):
        return redirect(url_for('index'))
    
    target_user = users.get(username)
    if target_user:
        current_status = target_user.get('can_upload', False)
        target_user['can_upload'] = not current_status
        save_data()
        
        status_text = "erteilt" if not current_status else "entzogen"
        log_activity(session['user'], "Admin", f"Upload-Recht für {username} {status_text}")
        flash(f"Upload-Recht für '{username}' wurde {status_text}.", "success")
    
    return redirect(url_for('admin_users'))

# ------------------------------------------------------------------------------
# 10. APP START
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    # Nur für lokale Entwicklung
    app.run(debug=True, host='0.0.0.0', port=5000)