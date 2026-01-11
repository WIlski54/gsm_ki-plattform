"""
KI-Projekt-Plattform für Schulen
Eine Austauschplattform für KI-Projekte unter Kollegen
Mit Login-System, Admin-Dashboard und Token-System
"""

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Konfiguration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'html', 'htm', 'css', 'js', 'py', 'zip', 'pdf', 'md', 'txt', 'json'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max

# Datendateien
PROJECTS_FILE = 'projects.json'
USERS_FILE = 'users.json'
ACTIVITY_FILE = 'activity.json'
SETTINGS_FILE = 'settings.json'

# Fachbereiche / Kategorien
CATEGORIES = {
    'naturwissenschaften': {
        'name': 'Naturwissenschaften',
        'icon': '🔬',
        'description': 'Chemie, Physik, Biologie',
        'color': 'emerald',
        'subjects': ['Chemie', 'Physik', 'Biologie']
    },
    'sprachen': {
        'name': 'Sprachen',
        'icon': '📚',
        'description': 'Deutsch, Englisch, Fremdsprachen',
        'color': 'blue',
        'subjects': ['Deutsch', 'Englisch', 'Französisch', 'Spanisch', 'Latein']
    },
    'gesellschaft': {
        'name': 'Gesellschaftswissenschaften',
        'icon': '🌍',
        'description': 'Geschichte, Politik, Erdkunde',
        'color': 'amber',
        'subjects': ['Geschichte', 'Politik', 'Erdkunde', 'Sozialwissenschaften']
    },
    'mathematik': {
        'name': 'Mathematik & Informatik',
        'icon': '📐',
        'description': 'Mathematik, Informatik, Technik',
        'color': 'violet',
        'subjects': ['Mathematik', 'Informatik', 'Technik']
    },
    'kunst-musik': {
        'name': 'Kunst & Musik',
        'icon': '🎨',
        'description': 'Kunst, Musik, Theater',
        'color': 'rose',
        'subjects': ['Kunst', 'Musik', 'Darstellendes Spiel']
    },
    'sonstiges': {
        'name': 'Fächerübergreifend',
        'icon': '✨',
        'description': 'Allgemeine Tools & Projekte',
        'color': 'slate',
        'subjects': ['Allgemein', 'Verwaltung', 'Organisation']
    }
}

# Einheitliche Materialtypen für alle Fächer
MATERIAL_TYPES = [
    {'id': 'folie', 'name': 'Folie/Poster', 'icon': '🖼️'},
    {'id': 'arbeitsblatt', 'name': 'Arbeitsblatt', 'icon': '📝'},
    {'id': 'interaktiv', 'name': 'Arbeitsblatt (interaktiv)', 'icon': '🎮'},
    {'id': 'ki', 'name': 'Arbeitsblatt (KI)', 'icon': '🤖'}
]

# Standard Token-Einstellungen
DEFAULT_SETTINGS = {
    'initial_tokens': 3,      # Start-Token für neue User
    'download_cost': 1,       # Token-Kosten pro Download
    'upload_reward': 1        # Token-Belohnung pro Upload
}

# =============================================================================
# Hilfsfunktionen für Datenpersistenz
# =============================================================================

def load_json(filepath, default=None):
    """Lädt JSON-Datei, gibt default zurück wenn nicht vorhanden"""
    if default is None:
        default = []
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(filepath, data):
    """Speichert Daten in JSON-Datei"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_projects():
    return load_json(PROJECTS_FILE, [])

def save_projects(projects):
    save_json(PROJECTS_FILE, projects)

def load_users():
    return load_json(USERS_FILE, {})

def save_users(users):
    save_json(USERS_FILE, users)

def load_activity():
    return load_json(ACTIVITY_FILE, [])

def save_activity(activity):
    save_json(ACTIVITY_FILE, activity)

def load_settings():
    settings = load_json(SETTINGS_FILE, {})
    # Merge mit Defaults
    for key, value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = value
    return settings

def save_settings(settings):
    save_json(SETTINGS_FILE, settings)

# =============================================================================
# Token-System
# =============================================================================

def get_user_tokens(username):
    """Gibt Token-Anzahl eines Users zurück"""
    users = load_users()
    user = users.get(username, {})
    return user.get('tokens', 0)

def set_user_tokens(username, tokens):
    """Setzt Token-Anzahl für einen User"""
    users = load_users()
    if username in users:
        users[username]['tokens'] = max(0, tokens)  # Nie negativ
        save_users(users)
        return True
    return False

def add_user_tokens(username, amount):
    """Fügt Tokens hinzu"""
    users = load_users()
    if username in users:
        current = users[username].get('tokens', 0)
        users[username]['tokens'] = current + amount
        save_users(users)
        return users[username]['tokens']
    return 0

def deduct_user_tokens(username, amount):
    """Zieht Tokens ab, gibt True zurück wenn erfolgreich"""
    users = load_users()
    if username in users:
        current = users[username].get('tokens', 0)
        if current >= amount:
            users[username]['tokens'] = current - amount
            save_users(users)
            return True
    return False

def can_download(username):
    """Prüft ob User downloaden kann (genug Tokens oder Admin)"""
    users = load_users()
    user = users.get(username, {})
    if user.get('role') == 'admin':
        return True
    settings = load_settings()
    return user.get('tokens', 0) >= settings.get('download_cost', 1)

# =============================================================================
# Aktivitäts-Logging
# =============================================================================

def log_activity(action, details="", user=None):
    """Loggt eine Aktivität"""
    activity = load_activity()
    entry = {
        'id': len(activity) + 1,
        'timestamp': datetime.now().isoformat(),
        'action': action,
        'details': details,
        'user': user or session.get('username', 'Anonym'),
        'ip': request.remote_addr if request else None
    }
    activity.insert(0, entry)
    activity = activity[:500]
    save_activity(activity)
    return entry

# =============================================================================
# Authentifizierung
# =============================================================================

def init_admin():
    """Erstellt Admin-Account falls nicht vorhanden"""
    users = load_users()
    if 'admin' not in users:
        users['admin'] = {
            'password': generate_password_hash('admin123'),
            'role': 'admin',
            'name': 'Administrator',
            'tokens': 999999,  # Admin hat unbegrenzt
            'created': datetime.now().isoformat()
        }
        save_users(users)
        print("=" * 60)
        print("⚠️  Admin-Account erstellt!")
        print("   Benutzername: admin")
        print("   Passwort: admin123")
        print("   Bitte Passwort nach erstem Login ändern!")
        print("=" * 60)
    
    # Settings initialisieren
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)

def login_required(f):
    """Decorator für geschützte Routen"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Bitte melde dich an.', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator für Admin-Routen"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Bitte melde dich an.', 'error')
            return redirect(url_for('login'))
        users = load_users()
        user = users.get(session.get('user_id'), {})
        if user.get('role') != 'admin':
            flash('Zugriff verweigert.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Gibt aktuellen User zurück oder None"""
    if 'user_id' not in session:
        return None
    users = load_users()
    user = users.get(session.get('user_id'))
    if user:
        user['username'] = session.get('user_id')
    return user

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_icon(filename):
    if not filename:
        return '📄'
    ext = filename.rsplit('.', 1)[-1].lower()
    icons = {
        'html': '🌐', 'htm': '🌐', 'css': '🎨', 'js': '⚡',
        'py': '🐍', 'zip': '📦', 'pdf': '📄', 'md': '📝',
        'txt': '📃', 'json': '📋'
    }
    return icons.get(ext, '📎')

# Jinja2 Context Processor
@app.context_processor
def inject_globals():
    user = get_current_user()
    settings = load_settings()
    return dict(
        current_user=user, 
        is_admin=user and user.get('role') == 'admin',
        material_types=MATERIAL_TYPES,
        token_settings=settings,
        user_tokens=user.get('tokens', 0) if user else 0,
        can_user_download=can_download(session.get('user_id')) if user else False
    )

# Jinja2 Filter
app.jinja_env.globals['get_file_icon'] = get_file_icon

# Upload-Ordner erstellen
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Admin initialisieren
init_admin()

# =============================================================================
# Auth-Routen
# =============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        
        users = load_users()
        user = users.get(username)
        
        if user and check_password_hash(user.get('password', ''), password):
            session['user_id'] = username
            session['username'] = user.get('name', username)
            session['role'] = user.get('role', 'user')
            log_activity('login', f'Login erfolgreich', username)
            flash(f'Willkommen, {user.get("name", username)}!', 'success')
            next_url = request.args.get('next', url_for('index'))
            return redirect(next_url)
        else:
            log_activity('login_failed', f'Fehlgeschlagen für: {username}')
            flash('Ungültige Anmeldedaten.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    username = session.get('user_id', 'Unbekannt')
    log_activity('logout', 'Logout', username)
    session.clear()
    flash('Du wurdest abgemeldet.', 'success')
    return redirect(url_for('login'))

# =============================================================================
# Hauptseiten
# =============================================================================

@app.route('/')
@login_required
def index():
    projects = load_projects()
    
    stats = {}
    for cat_id in CATEGORIES:
        cat_projects = [p for p in projects if p.get('category') == cat_id]
        stats[cat_id] = {
            'count': len(cat_projects),
            'downloads': sum(p.get('downloads', 0) for p in cat_projects)
        }
    
    return render_template('index.html',
                         categories=CATEGORIES,
                         stats=stats,
                         recent_projects=sorted(projects, key=lambda x: x.get('created', ''), reverse=True)[:6])

@app.route('/kategorie/<category_id>')
@login_required
def category(category_id):
    if category_id not in CATEGORIES:
        flash('Kategorie nicht gefunden', 'error')
        return redirect(url_for('index'))
    
    projects = load_projects()
    category_projects = [p for p in projects if p.get('category') == category_id]
    
    return render_template('category.html',
                         category=CATEGORIES[category_id],
                         category_id=category_id,
                         categories=CATEGORIES,
                         projects=category_projects)

@app.route('/suche')
@login_required
def search():
    query = request.args.get('q', '').strip().lower()
    projects = load_projects()
    
    if query:
        results = []
        for p in projects:
            searchable = f"{p.get('title', '')} {p.get('description', '')} {' '.join(p.get('tags', []))}".lower()
            if query in searchable:
                results.append(p)
    else:
        results = []
    
    return render_template('search.html',
                         query=query,
                         results=results,
                         categories=CATEGORIES)

@app.route('/projekt/<int:project_id>')
@login_required
def project_detail(project_id):
    projects = load_projects()
    project = next((p for p in projects if p.get('id') == project_id), None)
    
    if not project:
        flash('Projekt nicht gefunden', 'error')
        return redirect(url_for('index'))
    
    return render_template('project.html', 
                         project=project, 
                         categories=CATEGORIES)

@app.route('/download/<int:project_id>')
@login_required
def download_file(project_id):
    """Download einer Projektdatei - mit Token-System"""
    projects = load_projects()
    project = next((p for p in projects if p.get('id') == project_id), None)
    
    if not project or not project.get('filename'):
        flash('Datei nicht gefunden', 'error')
        return redirect(url_for('index'))
    
    username = session.get('user_id')
    users = load_users()
    user = users.get(username, {})
    settings = load_settings()
    
    # Admin braucht keine Tokens
    if user.get('role') != 'admin':
        download_cost = settings.get('download_cost', 1)
        
        if not deduct_user_tokens(username, download_cost):
            flash(f'Nicht genug Tokens! Du benötigst {download_cost} Token für diesen Download.', 'error')
            return redirect(url_for('project_detail', project_id=project_id))
        
        log_activity('token_spent', f'-{download_cost} Token für Download: {project.get("title")}', username)
    
    # Download-Zähler erhöhen
    project['downloads'] = project.get('downloads', 0) + 1
    save_projects(projects)
    
    log_activity('download', f'{project.get("title")}', username)
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], 
                              project['filename'],
                              as_attachment=True)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload-Seite für neue Projekte - mit Token-Belohnung"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category_id = request.form.get('category')
        subject = request.form.get('subject', '').strip()
        material_type = request.form.get('material_type', '').strip()
        author = request.form.get('author', session.get('username', 'Anonym')).strip()
        tags = request.form.get('tags', '').strip()
        project_url = request.form.get('project_url', '').strip()
        
        if not title or not category_id or not material_type:
            flash('Titel, Kategorie und Materialtyp sind erforderlich', 'error')
            return redirect(url_for('upload'))
        
        file = request.files.get('file')
        filename = None
        
        if file and file.filename:
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                base, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{base}_{timestamp}{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            else:
                flash('Dateityp nicht erlaubt', 'error')
                return redirect(url_for('upload'))
        
        # Mindestens Datei oder URL erforderlich
        if not filename and not project_url:
            flash('Bitte lade eine Datei hoch oder gib eine Projekt-URL an.', 'error')
            return redirect(url_for('upload'))
        
        projects = load_projects()
        new_id = max([p.get('id', 0) for p in projects], default=0) + 1
        
        new_project = {
            'id': new_id,
            'title': title,
            'description': description,
            'category': category_id,
            'subject': subject,
            'material_type': material_type,
            'author': author,
            'tags': [t.strip() for t in tags.split(',') if t.strip()],
            'filename': filename,
            'project_url': project_url if project_url else None,
            'created': datetime.now().isoformat(),
            'downloads': 0,
            'uploaded_by': session.get('user_id')
        }
        
        projects.append(new_project)
        save_projects(projects)
        
        # Token-Belohnung für Upload (außer Admin)
        username = session.get('user_id')
        users = load_users()
        user = users.get(username, {})
        settings = load_settings()
        
        if user.get('role') != 'admin':
            upload_reward = settings.get('upload_reward', 1)
            new_tokens = add_user_tokens(username, upload_reward)
            log_activity('token_earned', f'+{upload_reward} Token für Upload: {title}', username)
            flash(f'Projekt erfolgreich hochgeladen! Du hast {upload_reward} Token verdient. (Aktuell: {new_tokens} Tokens)', 'success')
        else:
            flash('Projekt erfolgreich hochgeladen!', 'success')
        
        log_activity('project_uploaded', f'{title}')
        return redirect(url_for('category', category_id=category_id))
    
    return render_template('upload.html', categories=CATEGORIES)

# =============================================================================
# Admin-Routen
# =============================================================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin-Dashboard"""
    projects = load_projects()
    users = load_users()
    activity = load_activity()
    settings = load_settings()
    
    total_downloads = sum(p.get('downloads', 0) for p in projects)
    
    downloads_by_cat = {}
    for cat_id, cat in CATEGORIES.items():
        cat_projects = [p for p in projects if p.get('category') == cat_id]
        downloads_by_cat[cat_id] = {
            'name': cat['name'],
            'icon': cat['icon'],
            'downloads': sum(p.get('downloads', 0) for p in cat_projects)
        }
    
    top_projects = sorted(projects, key=lambda x: x.get('downloads', 0), reverse=True)[:5]
    today = datetime.now().date().isoformat()
    views_today = len([a for a in activity if a.get('timestamp', '').startswith(today)])
    
    # Token-Statistiken
    total_tokens = sum(u.get('tokens', 0) for u in users.values() if u.get('role') != 'admin')
    
    return render_template('admin/dashboard.html',
                         categories=CATEGORIES,
                         total_projects=len(projects),
                         total_downloads=total_downloads,
                         total_users=len(users),
                         views_today=views_today,
                         downloads_by_cat=downloads_by_cat,
                         top_projects=top_projects,
                         recent_activity=activity[:15],
                         settings=settings,
                         total_tokens=total_tokens)

@app.route('/admin/projekte')
@admin_required
def admin_projects():
    """Projektverwaltung"""
    projects = load_projects()
    projects = sorted(projects, key=lambda x: x.get('created', ''), reverse=True)
    return render_template('admin/projects.html',
                         categories=CATEGORIES,
                         projects=projects)

@app.route('/admin/projekte/<int:project_id>/delete', methods=['POST'])
@admin_required
def admin_delete_project(project_id):
    """Projekt löschen"""
    projects = load_projects()
    project = next((p for p in projects if p.get('id') == project_id), None)
    
    if project:
        if project.get('filename'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], project['filename'])
            if os.path.exists(filepath):
                os.remove(filepath)
        
        projects = [p for p in projects if p.get('id') != project_id]
        save_projects(projects)
        log_activity('project_deleted', f'Projekt gelöscht: {project.get("title")}')
        flash('Projekt gelöscht.', 'success')
    else:
        flash('Projekt nicht gefunden.', 'error')
    
    return redirect(url_for('admin_projects'))

@app.route('/admin/benutzer')
@admin_required
def admin_users():
    """Benutzerverwaltung"""
    users = load_users()
    settings = load_settings()
    return render_template('admin/users.html',
                         categories=CATEGORIES,
                         users=users,
                         settings=settings)

@app.route('/admin/benutzer/neu', methods=['GET', 'POST'])
@admin_required
def admin_create_user():
    """Neuen Benutzer anlegen"""
    settings = load_settings()
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()
        role = request.form.get('role', 'user')
        tokens = int(request.form.get('tokens', settings.get('initial_tokens', 3)))
        
        if not username or not password:
            flash('Benutzername und Passwort erforderlich.', 'error')
            return redirect(url_for('admin_create_user'))
        
        if len(password) < 6:
            flash('Passwort muss mindestens 6 Zeichen haben.', 'error')
            return redirect(url_for('admin_create_user'))
        
        users = load_users()
        if username in users:
            flash('Benutzername bereits vergeben.', 'error')
            return redirect(url_for('admin_create_user'))
        
        users[username] = {
            'password': generate_password_hash(password),
            'role': role,
            'name': name or username,
            'tokens': 999999 if role == 'admin' else tokens,
            'created': datetime.now().isoformat()
        }
        save_users(users)
        log_activity('user_created', f'Neuer Benutzer: {username} (Tokens: {tokens})')
        flash(f'Benutzer "{username}" erstellt mit {tokens} Tokens.', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/user_form.html', 
                         categories=CATEGORIES, 
                         edit_user=None,
                         settings=settings)

@app.route('/admin/benutzer/<username>/tokens', methods=['POST'])
@admin_required
def admin_set_user_tokens(username):
    """Token-Anzahl für Benutzer setzen"""
    tokens = int(request.form.get('tokens', 0))
    
    users = load_users()
    if username in users and users[username].get('role') != 'admin':
        old_tokens = users[username].get('tokens', 0)
        users[username]['tokens'] = tokens
        save_users(users)
        log_activity('tokens_adjusted', f'{username}: {old_tokens} → {tokens} Tokens')
        flash(f'Tokens für {username} auf {tokens} gesetzt.', 'success')
    else:
        flash('Benutzer nicht gefunden oder Admin.', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/benutzer/<username>/delete', methods=['POST'])
@admin_required
def admin_delete_user(username):
    """Benutzer löschen"""
    if username == session.get('user_id'):
        flash('Du kannst dich nicht selbst löschen.', 'error')
        return redirect(url_for('admin_users'))
    
    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
        log_activity('user_deleted', f'Benutzer gelöscht: {username}')
        flash('Benutzer gelöscht.', 'success')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/aktivitaet')
@admin_required
def admin_activity():
    """Aktivitätslog"""
    activity = load_activity()
    
    action_filter = request.args.get('action')
    if action_filter:
        activity = [a for a in activity if a.get('action') == action_filter]
    
    all_actions = list(set(a.get('action') for a in load_activity()))
    
    return render_template('admin/activity.html',
                         categories=CATEGORIES,
                         activity=activity[:100],
                         action_filter=action_filter,
                         all_actions=sorted(all_actions))

@app.route('/admin/einstellungen', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    """Admin-Einstellungen inkl. Token-System"""
    settings = load_settings()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            users = load_users()
            user = users.get(session.get('user_id'))
            
            if not check_password_hash(user.get('password', ''), current_password):
                flash('Aktuelles Passwort ist falsch.', 'error')
            elif new_password != confirm_password:
                flash('Passwörter stimmen nicht überein.', 'error')
            elif len(new_password) < 6:
                flash('Neues Passwort muss mindestens 6 Zeichen haben.', 'error')
            else:
                users[session.get('user_id')]['password'] = generate_password_hash(new_password)
                save_users(users)
                log_activity('password_changed', 'Admin-Passwort geändert')
                flash('Passwort erfolgreich geändert.', 'success')
        
        elif action == 'save_token_settings':
            settings['initial_tokens'] = int(request.form.get('initial_tokens', 3))
            settings['download_cost'] = int(request.form.get('download_cost', 1))
            settings['upload_reward'] = int(request.form.get('upload_reward', 1))
            save_settings(settings)
            log_activity('settings_changed', f'Token-Einstellungen geändert: Start={settings["initial_tokens"]}, Kosten={settings["download_cost"]}, Belohnung={settings["upload_reward"]}')
            flash('Token-Einstellungen gespeichert.', 'success')
        
        return redirect(url_for('admin_settings'))
    
    users = load_users()
    user = users.get(session.get('user_id'), {})
    
    return render_template('admin/settings.html',
                         categories=CATEGORIES,
                         user=user,
                         settings=settings)

# =============================================================================
# API-Routen
# =============================================================================

@app.route('/api/projects')
@login_required
def api_projects():
    projects = load_projects()
    return jsonify(projects)

@app.route('/api/user/tokens')
@login_required
def api_user_tokens():
    """Gibt aktuelle Token-Anzahl zurück"""
    username = session.get('user_id')
    users = load_users()
    user = users.get(username, {})
    settings = load_settings()
    
    return jsonify({
        'tokens': user.get('tokens', 0),
        'is_admin': user.get('role') == 'admin',
        'download_cost': settings.get('download_cost', 1),
        'upload_reward': settings.get('upload_reward', 1),
        'can_download': can_download(username)
    })

# =============================================================================
# Error Handler
# =============================================================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', 
                         error_code=404, 
                         error_message='Seite nicht gefunden',
                         categories=CATEGORIES), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('error.html', 
                         error_code=500, 
                         error_message='Interner Serverfehler',
                         categories=CATEGORIES), 500

# =============================================================================
# App Start
# =============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
