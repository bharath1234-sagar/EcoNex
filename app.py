import os, json, sqlite3, hashlib
from datetime import date, datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "econex-carbon-os-backend-secret-2026")

BASE = Path(__file__).resolve().parent
DB = BASE / 'econex.db'
UPLOAD_FOLDER = BASE / 'static' / 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)

def hash_pw(pw):
    return hashlib.sha256(pw.encode('utf-8')).hexdigest()

PROFILES = {
    'Household': {
        'icon': '🏡', 'label': 'Household / Family', 'badge': 'Residential',
        'fields': [('electricity', 'Grid Electricity', 'kWh', 0.82), ('lpg', 'Cooking LPG', 'kg', 3.00), ('car', 'Private Car Travel', 'km', 0.17), ('waste', 'Municipal Mixed Waste', 'kg', 0.50)]
    },
    'City Resident': {
        'icon': '🚲', 'label': 'Urban Working Professional', 'badge': 'Commuter',
        'fields': [('electricity', 'Apartment Power', 'kWh', 0.82), ('car', 'Cab / Car Travel', 'km', 0.17), ('bus', 'Metro & City Bus', 'km', 0.08), ('waste', 'Mixed Waste', 'kg', 0.50)]
    },
    'Student / Campus': {
        'icon': '🎓', 'label': 'Student & Campus Hosteller', 'badge': 'Education',
        'fields': [('electricity', 'Hostel Electricity', 'kWh', 0.82), ('bus', 'Campus Shuttle / Bus', 'km', 0.08), ('waste', 'Hostel Waste', 'kg', 0.50), ('solar', 'Rooftop Solar Offset', 'kWh', -0.82)]
    },
    'College / Institution': {
        'icon': '🏫', 'label': 'College / Organization Admin', 'badge': 'Campus Admin',
        'fields': [('electricity', 'Campus Grid Power', 'kWh', 0.82), ('diesel', 'Generator / Fleet Diesel', 'litres', 2.68), ('car', 'Institutional Travel', 'km', 0.17), ('waste', 'Campus Landfill Waste', 'kg', 0.50)]
    },
    'Farmer / Dairy Farm': {
        'icon': '🌾', 'label': 'Farmer & Dairy Producer', 'badge': 'Agriculture',
        'fields': [('electricity', 'Irrigation Pump Power', 'kWh', 0.82), ('diesel', 'Tractor & Machinery Diesel', 'litres', 2.68), ('fertilizer', 'Nitrogen Fertilizer', 'kg', 5.50), ('livestock', 'Livestock Units', 'head', 100.0)]
    },
    'Industry': {
        'icon': '🏭', 'label': 'Industrial / Manufacturing Plant', 'badge': 'Enterprise',
        'fields': [('electricity', '3-Phase Grid Electricity', 'kWh', 0.82), ('diesel', 'Boiler / Generator Diesel', 'litres', 2.68), ('waste', 'Industrial Solid Waste', 'kg', 0.50), ('water', 'Industrial Water Use', 'kL', 0.34)]
    }
}

ACTIVITIES = {
    'electricity': ('Grid Electricity', 'kWh', 0.82),
    'diesel': ('Diesel / Generator Fuel', 'litres', 2.68),
    'lpg': ('LPG Cylinder', 'kg', 3.00),
    'car': ('Petrol / Diesel Car Travel', 'km', 0.17),
    'bus': ('Bus / Metro Transit', 'km', 0.08),
    'waste': ('Mixed Waste to Landfill', 'kg', 0.50),
    'water': ('Water Usage', 'kL', 0.34),
    'fertilizer': ('Nitrogen Fertilizer', 'kg', 5.50),
    'livestock': ('Livestock Emission Factor', 'animal unit', 100.0),
    'solar': ('Solar Clean Energy Offset', 'kWh', -0.82)
}

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = conn()
    try:
        cur = c.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                password_hash TEXT,
                name TEXT,
                picture TEXT,
                profile_category TEXT DEFAULT 'City Resident',
                org TEXT DEFAULT '',
                location TEXT DEFAULT 'Bengaluru',
                language TEXT DEFAULT 'en'
            );
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                day TEXT,
                period TEXT,
                profile TEXT,
                payload TEXT,
                total REAL
            );
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                day TEXT,
                title TEXT,
                category TEXT,
                saved REAL,
                note TEXT
            );
            CREATE TABLE IF NOT EXISTS challenge_done (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                done INTEGER DEFAULT 0,
                UNIQUE(user_id, title)
            );
            CREATE TABLE IF NOT EXISTS user_simulation (
                user_id INTEGER PRIMARY KEY,
                slider1 INTEGER DEFAULT 8,
                slider2 INTEGER DEFAULT 6,
                slider3 INTEGER DEFAULT 5,
                saved_co2 REAL DEFAULT 48.2,
                saved_inr INTEGER DEFAULT 1850
            );
            CREATE TABLE IF NOT EXISTS adopted_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                category TEXT,
                saved REAL,
                adopted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, title)
            );
        """)
        c.commit()

        # Seed initial real user accounts
        demo_pw = hash_pw('password123')
        cur.execute("INSERT OR IGNORE INTO users(id, email, password_hash, name, picture, profile_category, org, location, language) VALUES(1, 'bharath@gmail.com', ?, 'Bharath Sagar', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80', 'City Resident', 'GreenTech Bengaluru', 'Bengaluru', 'en')", (demo_pw,))
        cur.execute("INSERT OR IGNORE INTO users(id, email, password_hash, name, picture, profile_category, org, location, language) VALUES(2, 'ananya.sharma@gmail.com', ?, 'Ananya Sharma', 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150&auto=format&fit=crop&q=80', 'Student / Campus', 'RVCE Campus', 'Bengaluru', 'en')", (demo_pw,))
        cur.execute("INSERT OR IGNORE INTO user_simulation(user_id, slider1, slider2, slider3, saved_co2, saved_inr) VALUES(1, 8, 6, 5, 48.2, 1850)")
        cur.execute("INSERT OR IGNORE INTO user_simulation(user_id, slider1, slider2, slider3, saved_co2, saved_inr) VALUES(2, 12, 4, 8, 62.4, 2300)")
        c.commit()
    finally:
        c.close()

init_db()

@app.route('/auth/login', methods=['POST'])
def auth_login():
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    c = conn()
    try:
        cur = c.cursor()
        cur.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cur.fetchone()
        if not user or user['password_hash'] != hash_pw(password):
            flash('Invalid email or password.', 'error')
            return redirect(url_for('login'))
        session['user_id'] = user['id']
        session['lang'] = user['language'] or 'en'
    finally:
        c.close()
    return redirect(url_for('home'))

@app.route('/auth/register', methods=['POST'])
def auth_register():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    confirm = request.form.get('confirm_password', '')
    category = request.form.get('category', 'City Resident')

    if not name or not email or not password or password != confirm:
        flash('Invalid registration details.', 'error')
        return redirect(url_for('login') + '#register')

    c = conn()
    try:
        cur = c.cursor()
        cur.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cur.fetchone():
            flash('Email already exists.', 'error')
            return redirect(url_for('login'))
        pw_hash = hash_pw(password)
        avatar = 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80'
        cur.execute('INSERT INTO users(email, password_hash, name, picture, profile_category, org, location, language) VALUES(?, ?, ?, ?, ?, ?, ?, ?)',
                    (email, pw_hash, name, avatar, category, 'Eco Community', 'Bengaluru', 'en'))
        c.commit()
        cur.execute('SELECT id FROM users WHERE email = ?', (email,))
        user = cur.fetchone()
        session['user_id'] = user['id']
        cur.execute('INSERT INTO user_simulation(user_id) VALUES(?)', (user['id'],))
        c.commit()
    finally:
        c.close()
    return redirect(url_for('home'))

@app.route('/auth/demo')
def auth_demo():
    session['user_id'] = 1
    session['lang'] = 'en'
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.post('/activity/add')
def add_activity():
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    c = conn()
    try:
        cur = c.cursor()
        cur.execute('SELECT profile_category FROM users WHERE id = ?', (user_id,))
        user = cur.fetchone()
        profile = user['profile_category'] if user else 'City Resident'
        act_key = request.form.get('activity_key', '')
        quantity = max(0.0, float(request.form.get('quantity', 0) or 0))
        day = request.form.get('day') or date.today().isoformat()
        
        if act_key in ACTIVITIES and quantity > 0:
            factor = ACTIVITIES[act_key][2]
            total = round(quantity * factor, 3)
            payload = json.dumps({act_key: quantity})
            cur.execute('INSERT INTO activities(user_id, day, period, profile, payload, total) VALUES (?, ?, ?, ?, ?, ?)',
                        (user_id, day, day[:7], profile, payload, total))
            c.commit()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'status': 'success', 'day': day, 'item': ACTIVITIES[act_key][0], 'quantity': quantity, 'unit': ACTIVITIES[act_key][1], 'total': total})
    finally:
        c.close()
    return redirect(url_for('home'))

@app.post('/action/add')
def add_action():
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    title = request.form.get('title', 'Sustainable Action')[:100]
    category = request.form.get('category', 'Energy')[:50]
    saved = max(0.0, float(request.form.get('saved', 0) or 0))
    note = request.form.get('note', '')[:200]
    day = request.form.get('day') or date.today().isoformat()
    
    c = conn()
    try:
        cur = c.cursor()
        cur.execute('INSERT INTO actions(user_id, day, title, category, saved, note) VALUES (?, ?, ?, ?, ?, ?)',
                    (user_id, day, title, category, saved, note))
        cur.execute('INSERT OR IGNORE INTO adopted_recommendations(user_id, title, category, saved) VALUES (?, ?, ?, ?)',
                    (user_id, title, category, saved))
        c.commit()
        cur.execute('SELECT coalesce(sum(saved), 0) as tot_saved FROM actions WHERE user_id = ?', (user_id,))
        new_tot = round(cur.fetchone()['tot_saved'], 1)
    finally:
        c.close()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'status': 'success', 'saved': saved, 'total_saved': new_tot, 'title': title})
    return redirect(url_for('home'))

@app.post('/challenge/quick_log')
def challenge_quick_log():
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    title = request.form.get('title', 'Challenge Activity')
    category = request.form.get('category', 'General')
    saved = float(request.form.get('saved', 1.5))
    day = date.today().isoformat()

    c = conn()
    try:
        cur = c.cursor()
        cur.execute('INSERT INTO actions(user_id, day, title, category, saved, note) VALUES (?, ?, ?, ?, ?, ?)',
                    (user_id, day, title, category, saved, 'Logged via Challenge micro-action'))
        c.commit()
        cur.execute('SELECT coalesce(sum(saved), 0) as tot_saved FROM actions WHERE user_id = ?', (user_id,))
        new_tot = round(cur.fetchone()['tot_saved'], 1)
    finally:
        c.close()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'status': 'success', 'saved': saved, 'total_saved': new_tot, 'title': title})
    return redirect(url_for('home'))

@app.route('/api/ai_chat', methods=['POST'])
def ai_chat():
    data = request.get_json(force=True, silent=True) or request.form or {}
    query = str(data.get('message') or '').strip().lower()
    reply = f"EcoNex AI Advisor: Received query about '{query}'. Focus on reducing grid power and transit emissions!"
    return jsonify({'reply': reply})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)