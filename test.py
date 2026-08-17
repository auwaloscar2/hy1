import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'zaria_hyfam_secure_secret_key_production'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('school_portal.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            class_name TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            admission_no TEXT NOT NULL,
            class_name TEXT NOT NULL,
            fee REAL DEFAULT 0,
            parent_name TEXT,
            phone TEXT,
            email TEXT,
            relation TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_archives (
            archive_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            full_name TEXT NOT NULL,
            admission_no TEXT NOT NULL,
            class_name TEXT NOT NULL,
            term TEXT NOT NULL,
            academic_year TEXT NOT NULL,
            total_score REAL,
            grade_summary TEXT,
            archived_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute("PRAGMA table_info(students)")
    existing_columns = [col['name'] for col in cursor.fetchall()]
    if existing_columns:
        if 'fee' not in existing_columns:
            cursor.execute("ALTER TABLE students ADD COLUMN fee REAL DEFAULT 0")
        if 'parent_name' not in existing_columns:
            cursor.execute("ALTER TABLE students ADD COLUMN parent_name TEXT")
        if 'phone' not in existing_columns:
            cursor.execute("ALTER TABLE students ADD COLUMN phone TEXT")
        if 'email' not in existing_columns:
            cursor.execute("ALTER TABLE students ADD COLUMN email TEXT")
        if 'relation' not in existing_columns:
            cursor.execute("ALTER TABLE students ADD COLUMN relation TEXT")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT NOT NULL,
            subject_name TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            term TEXT,
            subject TEXT,
            ca1_score REAL DEFAULT 0,
            ca2_score REAL DEFAULT 0,
            exam_score REAL DEFAULT 0,
            total_score REAL,
            grade TEXT,
            remarks TEXT,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    ''')

    all_classes = [
        "Creche", "Nursery", "Primary", "Secondary",
        "Kindergarten 1", "Kindergarten 2", "Nursery 1", "Nursery 2",
        "Primary 1", "Primary 2", "Primary 3", "Primary 4", "Primary 5", "Primary 6",
        "JSS 1", "JSS 2", "JSS 3", "SS 1", "SS 2", "SS 3"
    ]

    default_hashed_pw = generate_password_hash('password123')

    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        admin_pw = generate_password_hash('adminhyfam2026')
        cursor.execute("INSERT INTO users (username, password_hash, role, class_name) VALUES (?, ?, ?, ?)", 
                       ('admin', admin_pw, 'admin', None))

    for cls in all_classes:
        uname = f"teacher_{cls.lower().replace(' ', '')}"
        cursor.execute("SELECT * FROM users WHERE username = ?", (uname,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (username, password_hash, role, class_name) VALUES (?, ?, ?, ?)",
                (uname, default_hashed_pw, 'teacher', cls)
            )

    conn.commit()
    conn.close()

init_db()

def calculate_grade(total):
    if total >= 75: return 'A', 'Excellent.'
    elif total >= 65: return 'B', 'Very Good.'
    elif total >= 50: return 'C', 'Credit.'
    elif total >= 40: return 'D', 'Pass.'
    else: return 'F', 'Fail. Required improvement.'

def ordinal_suffix(n):
    if 11 <= n <= 13:
        return f"{n}th"
    else:
        suffixes = {1: 'st', 2: 'nd', 3: 'rd'}
        return f"{n}{suffixes.get(n % 10, 'th')}"

UNIFIED_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Portal - Zaria Hyfam International School</title>
    <style>
        :root {
            --primary-navy: #1e3a8a;
            --primary-light: #3b82f6;
            --accent-gold: #f59e0b;
            --success: #10b981;
            --danger: #ef4444;
            --neutral-bg: #f8fafc;
            --white: #ffffff;
            --text-main: #1e293b;
            --border-color: #e2e8f0;
            --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: var(--neutral-bg); color: var(--text-main); line-height: 1.6; display: flex; flex-direction: column; min-height: 100vh; }
        .container { flex: 1; width: 100%; max-width: 1200px; margin: 0 auto; padding: 40px 20px; }
        nav { background-color: var(--primary-navy); display: flex; justify-content: space-between; align-items: center; padding: 15px 40px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); position: sticky; top: 0; z-index: 100; }
        .nav-logo { display: flex; align-items: center; gap: 15px; color: var(--white); font-size: 22px; font-weight: 700; font-family: 'Georgia', serif; }
        .nav-logo span { color: var(--accent-gold); }
        .img-logo img { border-radius: 50%; object-fit: cover; border: 2px solid var(--accent-gold); width: 60px; height: 60px; }
        .nav-links { display: flex; gap: 10px; align-items: center; }
        .nav-btn, .logout-btn { background: transparent; color: #93c5fd; border: 2px solid transparent; padding: 10px 20px; font-size: 15px; font-weight: 600; border-radius: 6px; cursor: pointer; text-decoration: none; display: inline-block; transition: all 0.3s; }
        .nav-btn:hover, .nav-btn.active { color: var(--white); background-color: var(--primary-light); border-color: var(--primary-light); }
        .portal-gate-btn { border: 1px dashed rgba(245, 158, 11, 0.4); }
        .page-section { display: none; animation: fadeIn 0.4s ease; }
        .page-section.active-section { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .form-card, .login-card { background: var(--white); border-radius: 10px; box-shadow: var(--card-shadow); overflow: hidden; margin-bottom: 30px; }
        .form-card { max-width: 850px; margin: 0 auto; }
        .login-card { max-width: 450px; margin: 60px auto; padding: 40px 30px; text-align: center; border-top: 5px solid var(--primary-light); }
        .form-header { background-color: var(--primary-navy); color: var(--white); padding: 30px 40px; }
        .form-header h2, .login-card h3 { font-family: 'Georgia', serif; margin-bottom: 8px; }
        .form-header p, .login-card p { color: #93c5fd; font-size: 14px; }
        .form-body { padding: 40px; }
        .section-title { font-size: 18px; font-weight: 700; color: var(--primary-navy); border-left: 4px solid var(--accent-gold); padding-left: 12px; margin: 30px 0 20px 0; text-transform: uppercase; }
        .form-group { margin-bottom: 20px; display: flex; flex-direction: column; gap: 8px; flex: 1; }
        .form-row { display: flex; gap: 20px; flex-wrap: wrap; }
        label { font-size: 14px; font-weight: 600; color: var(--text-main); }
        input, select { width: 100%; padding: 12px 16px; border: 1px solid var(--border-color); border-radius: 6px; font-size: 15px; color: var(--text-main); background-color: #f8fafc; }
        input:focus, select:focus { outline: none; border-color: var(--primary-light); background-color: var(--white); box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15); }
        .submit-btn { width: 100%; padding: 14px 28px; background-color: var(--primary-light); color: var(--white); border: none; border-radius: 6px; font-size: 16px; font-weight: 600; cursor: pointer; transition: background-color 0.3s; }
        .submit-btn:hover { background-color: #2563eb; }
        .logout-btn { border: 1px solid var(--danger); color: var(--danger); padding: 8px 16px; }
        .logout-btn:hover { background-color: var(--danger); color: var(--white); }
        .flash-messages { margin-bottom: 20px; }
        .flash-success { background: rgba(16,185,129,0.1); color: var(--success); padding: 12px; border-radius: 6px; border: 1px solid var(--success); margin-bottom: 10px; }
        .flash-error { background: rgba(239,68,68,0.1); color: var(--danger); padding: 12px; border-radius: 6px; border: 1px solid var(--danger); margin-bottom: 10px; }
        footer { background-color: #0f172a; color: #94a3b8; text-align: center; padding: 25px; font-size: 14px; margin-top: auto; border-top: 3px solid var(--accent-gold); }
    </style>
</head>
<body>
    <nav>
        <div class="nav-logo"> 
            <div class="img-logo"><img src="{{ url_for('static', filename='uploads/logo.jpg') }}?t={{ range(1000,9999)|random }}" alt="Logo" onerror="this.src='https://via.placeholder.com/60'"></div>
            Zaria Hyfam <span>School</span>
        </div>
        <div class="nav-links">
            <button class="nav-btn active" onclick="switchTab('home', this)">Home</button>
            <button class="nav-btn" onclick="switchTab('register', this)">Admissions</button>
            {% if session.get('username') %}
                <a href="{{ url_for('logout') }}" class="logout-btn">Logout ({{ session.get('username') }})</a>
            {% else %}
                <button class="nav-btn portal-gate-btn" onclick="switchTab('staff', this)">Staff Portal</button>
                <button class="nav-btn portal-gate-btn" onclick="switchTab('admin', this)">Admin Board</button>
            {% endif %}
        </div>
    </nav>

    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="flash-messages">
                    {% for cat, msg in messages %}
                        <div class="flash-{{ cat if cat in ['success','error'] else 'success' }}">{{ msg }}</div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}

        <!-- HOME TAB -->
        <div id="tab-home" class="page-section active-section">
            <div style="background-color: var(--white); padding: 50px 40px; border-radius: 8px; box-shadow: var(--card-shadow); text-align: center;">
                <h2 style="font-family: 'Georgia', serif; color: var(--primary-navy); font-size: 36px; margin-bottom: 12px;">Unified Academic Portal Console</h2>
                <p style="color: #64748b; margin-bottom: 30px; font-size: 16px;">Welcome to Zaria Hyfam International School portal management control architecture.</p>
                <div style="display: flex; gap: 15px; justify-content: center;">
                    <button class="submit-btn" style="max-width: 220px;" onclick="switchTab('register', document.querySelectorAll('.nav-btn')[1])">Student Enrollment</button>
                    <button class="submit-btn" style="max-width: 220px; background-color: var(--accent-gold); color: var(--primary-navy);" onclick="switchTab('staff', document.querySelectorAll('.nav-btn')[2])">Staff Entry Board</button>
                </div>
            </div>
        </div>

        <!-- ADMISSIONS TAB -->
        <div id="tab-register" class="page-section">
            <div class="form-card">
                <div class="form-header">
                    <h2>Student Admission Application</h2>
                    <p>Enter data profile to process admission status dossiers.</p>
                </div>
                <div class="form-body">
                    <form action="{{ url_for('register_student') }}" method="POST">
                        <div class="section-title" style="margin-top:0;">Parent / Guardian Information</div>
                        <div class="form-row">
                            <div class="form-group"><label>Parent First Name *</label><input type="text" name="p_fname" required></div>
                            <div class="form-group"><label>Parent Last Name *</label><input type="text" name="p_lname" required></div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Relationship *</label>
                                <select name="p_rel" required>
                                    <option value="" disabled selected>-- Select --</option>
                                    <option value="Father">Father</option>
                                    <option value="Mother">Mother</option>
                                    <option value="Legal Guardian">Legal Guardian</option>
                                </select>
                            </div>
                            <div class="form-group"><label>Active Email *</label><input type="email" name="p_email" required></div>
                        </div>
                        <div class="form-group"><label>Phone Number *</label><input type="tel" name="p_phone" placeholder="e.g. +234..." required></div>

                        <div class="section-title">Student Information</div>
                        <div class="form-row">
                            <div class="form-group"><label>Student First Name *</label><input type="text" name="s_fname" required></div>
                            <div class="form-group"><label>Student Last Name *</label><input type="text" name="s_lname" required></div>
                        </div>
                        <div class="form-row">
                            <div class="form-group"><label>Admission Number *</label><input type="text" name="admission_no" placeholder="e.g. HYFAM/2026/001" required></div>
                            <div class="form-group">
                                <label>Proposed Class *</label>
                                <select name="s_class" id="s_class" onchange="updateFee()" required>
                                    <option value="" disabled selected>-- Select Class --</option>
                                    <option value="Creche">Creche</option>
                                    <option value="Nursery">Nursery</option>
                                    <option value="Primary">Primary</option>
                                    <option value="Secondary">Secondary</option>
                                </select>
                                <div id="termFeeDisplay" style="margin-top: 8px; background-color: rgba(16, 185, 129, 0.1); color: var(--success); padding: 8px 14px; border-radius: 6px; font-weight: 700; display: none; border: 1px dashed var(--success);">Estimated Term Fee: ₦0.00</div>
                            </div>
                        </div>
                        <button type="submit" class="submit-btn">Submit Dossier</button>
                    </form>
                </div>
            </div>
        </div>

        <!-- STAFF LOGIN TAB -->
        <div id="tab-staff" class="page-section">
            <div class="login-card">
                <h3>Staff Gatekeeper</h3>
                <p>Input assigned security passphrase to manage student scorecards.</p>
                <form action="{{ url_for('login') }}" method="POST">
                    <input type="hidden" name="portal_type" value="staff">
                    <div class="form-group" style="text-align: left;"><label>Staff Username</label><input type="text" name="username" placeholder="e.g. teacher_primary" required></div>
                    <div class="form-group" style="text-align: left;"><label>Password</label><input type="password" name="password" placeholder="••••••••" required></div>
                    <button type="submit" class="submit-btn">Unlock Scoreboard</button>
                </form>
            </div>
        </div>

        <!-- ADMIN LOGIN TAB -->
        <div id="tab-admin" class="page-section">
            <div class="login-card">
                <h3>Admin Core Gateway</h3>
                <p>Input master administrator bypass phrase to unlock core system ledgers.</p>
                <form action="{{ url_for('login') }}" method="POST">
                    <input type="hidden" name="portal_type" value="admin">
                    <div class="form-group" style="text-align: left;"><label>Master Username</label><input type="text" name="username" value="admin" readonly></div>
                    <div class="form-group" style="text-align: left;"><label>Master Passphrase</label><input type="password" name="password" placeholder="••••••••" required></div>
                    <button type="submit" class="submit-btn">Unlock Core Board</button>
                </form>
            </div>
        </div>
    </div>

    <footer><p>© 2026 Zaria Hyfam International School Unified Database Portal system.</p></footer>

    <script>
        const feesMap = { "Creche": 45000, "Nursery": 55000, "Primary": 75000, "Secondary": 95000 };
        function updateFee() {
            let cls = document.getElementById('s_class').value;
            let display = document.getElementById('termFeeDisplay');
            if(feesMap[cls]) {
                display.innerText = "Estimated Term Fee: ₦" + feesMap[cls].toLocaleString();
                display.style.display = "inline-block";
            }
        }
        function switchTab(tabId, btn) {
            document.querySelectorAll('.page-section').forEach(sec => sec.classList.remove('active-section'));
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active-section');
            if(btn) btn.classList.add('active');
        }
    </script>
</body>
</html>"""

TEACHER_DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Staff Dashboard - Zaria Hyfam</title>
    <style>
        :root {
            --primary-navy: #1e3a8a; --primary-light: #3b82f6; --accent-gold: #f59e0b;
            --success: #10b981; --danger: #ef4444; --neutral-bg: #f8fafc; --white: #ffffff;
            --text-main: #1e293b; --text-muted: #64748b; --border-color: #e2e8f0; --card-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }
        body { font-family: 'Segoe UI', sans-serif; background: var(--neutral-bg); color: var(--text-main); margin: 0; padding: 0; }
        nav { background: var(--primary-navy); display: flex; justify-content: space-between; align-items: center; padding: 15px 40px; color: white; }
        .container { max-width: 1200px; margin: 30px auto; padding: 20px; }
        .form-card { background: white; border-radius: 10px; box-shadow: var(--card-shadow); margin-bottom: 30px; overflow: hidden; }
        .form-header { background: var(--primary-navy); color: white; padding: 20px 30px; }
        .form-body { padding: 30px; }
        .form-row { display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 15px; }
        .form-group { flex: 1; display: flex; flex-direction: column; gap: 6px; }
        input, select { padding: 10px; border: 1px solid var(--border-color); border-radius: 6px; }
        .submit-btn { background: var(--primary-light); color: white; border: none; padding: 12px 20px; border-radius: 6px; cursor: pointer; font-weight: 600; width: 100%; }
        .submit-btn:hover { background: #2563eb; }
        .logout-btn { color: white; background: transparent; border: 1px solid var(--danger); padding: 8px 16px; border-radius: 6px; text-decoration: none; }
        .table-wrapper { background: white; border-radius: 8px; box-shadow: var(--card-shadow); overflow-x: auto; margin-top: 15px; margin-bottom: 30px; }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th { background: #f1f5f9; color: var(--primary-navy); padding: 14px; }
        td { padding: 14px; border-bottom: 1px solid var(--border-color); }
        .flash { background: #d1fae5; color: #065f46; padding: 10px; border-radius: 6px; margin-bottom: 15px; }
        .action-btn { background: var(--accent-gold); color: var(--primary-navy); padding: 6px 12px; border-radius: 4px; text-decoration: none; font-weight: 600; font-size: 13px; display: inline-block; }
        .action-btn:hover { background: #d97706; color: white; }
        .delete-btn { background: var(--danger); color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 11px; }
    </style>
</head>
<body>
    <nav>
        <h2>Staff Desk: {{ class_name }}</h2>
        <a href="{{ url_for('logout') }}" class="logout-btn">Lock Desktop</a>
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages() %}
            {% if messages %}<div class="flash">{{ messages[0] }}</div>{% endif %}
        {% endwith %}

        <!-- STUDENT MANAGEMENT PANEL -->
        <div class="form-card">
            <div class="form-header"><h3>Manage Students for {{ class_name }}</h3></div>
            <div class="form-body">
                <form action="{{ url_for('add_student_direct') }}" method="POST" style="display: flex; gap: 15px; align-items: flex-end; margin-bottom: 20px;">
                    <div class="form-group" style="flex: 2;">
                        <label>Student Full Name *</label>
                        <input type="text" name="full_name" placeholder="e.g. Ibrahim Musa" required>
                    </div>
                    <div class="form-group" style="flex: 1;">
                        <label>Admission Number *</label>
                        <input type="text" name="admission_no" placeholder="e.g. HYFAM/2026/010" required>
                    </div>
                    <div class="form-group" style="flex: 1;">
                        <label>Parent Phone</label>
                        <input type="text" name="phone" placeholder="e.g. 0803...">
                    </div>
                    <button type="submit" class="submit-btn" style="width: auto; padding: 10px 25px;">Add Student</button>
                </form>
            </div>
        </div>

        <!-- SUBJECT MANAGEMENT PANEL -->
        <div class="form-card">
            <div class="form-header"><h3>Manage Subjects for {{ class_name }}</h3></div>
            <div class="form-body">
                <form action="{{ url_for('add_subject') }}" method="POST" style="display: flex; gap: 15px; align-items: flex-end; margin-bottom: 20px;">
                    <div class="form-group" style="flex: 1;">
                        <label>New Subject Name *</label>
                        <input type="text" name="subject_name" placeholder="e.g. Agricultural Science" required>
                    </div>
                    <button type="submit" class="submit-btn" style="width: auto; padding: 10px 25px;">Add Subject</button>
                </form>
                <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                    {% for sub in subjects %}
                        <div style="background: #f1f5f9; border: 1px solid var(--border-color); padding: 6px 12px; border-radius: 6px; display: flex; align-items: center; gap: 10px; font-size: 14px;">
                            <span>{{ sub }}</span>
                            <form action="{{ url_for('delete_subject') }}" method="POST" style="display:inline;" onsubmit="return confirm('Delete subject?');">
                                <input type="hidden" name="subject_name" value="{{ sub }}">
                                <button type="submit" class="delete-btn">×</button>
                            </form>
                        </div>
                    {% else %}
                        <p style="color: var(--text-muted); font-size: 14px;">No custom subjects added yet. Default subjects are active if none listed.</p>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- SCORE PROCESSOR PANEL -->
        <div class="form-card">
            <div class="form-header"><h3>Academic Score Processor & Multi-Year Archive Syncer</h3></div>
            <div class="form-body">
                <form action="{{ url_for('save_evaluation') }}" method="POST">
                    <div class="form-row">
                        <div class="form-group">
                            <label>Student *</label>
                            <select name="student_id" required>
                                <option value="" disabled selected>-- Select Student --</option>
                                {% for s in students %}
                                    <option value="{{ s.id }}">{{ s.full_name }} ({{ s.admission_no }})</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Subject *</label>
                            <select name="subject" required>
                                <option value="" disabled selected>-- Select Subject --</option>
                                {% for sub in subjects %}
                                    <option value="{{ sub }}">{{ sub }}</option>
                                {% endfor %}
                            </select>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>Term *</label><select name="term" required><option>First Term</option><option>Second Term</option><option>Third Term</option></select></div>
                        <div class="form-group"><label>Academic Year *</label><select name="academic_year" required><option>2025/2026 Academic Session</option><option>2026/2027 Academic Session</option><option>2027/2028 Academic Session</option></select></div>
                        <div class="form-group"><label>CA1 (Max 20)</label><input type="number" name="ca1" min="0" max="20" value="0" required></div>
                        <div class="form-group"><label>CA2 (Max 20)</label><input type="number" name="ca2" min="0" max="20" value="0" required></div>
                        <div class="form-group"><label>Exam (Max 60)</label><input type="number" name="exam" min="0" max="60" value="0" required></div>
                    </div>
                    <button type="submit" class="submit-btn">Compile & Archive Student Grade</button>
                </form>
            </div>
        </div>

        <div class="table-wrapper">
            <h3 style="padding: 20px; color: var(--primary-navy);">Class Students & Result Sheet Generator</h3>
            <table>
                <thead><tr><th>Student Name</th><th>Admission No</th><th>Parent Phone</th><th>Action Center</th></tr></thead>
                <tbody>
                    {% for s in students %}
                    <tr>
                        <td><strong>{{ s.full_name }}</strong></td>
                        <td>{{ s.admission_no }}</td>
                        <td>{{ s.phone or 'N/A' }}</td>
                        <td>
                            <div style="display: flex; gap: 10px; align-items: center;">
                                <form action="{{ url_for('print_result') }}" method="GET" style="display:inline-flex; gap:10px; align-items:center;">
                                    <input type="hidden" name="student_id" value="{{ s.id }}">
                                    <select name="term" style="padding:6px; font-size:13px; width:auto;">
                                        <option>First Term</option><option>Second Term</option><option>Third Term</option>
                                    </select>
                                    <button type="submit" class="action-btn">Print Report Sheet</button>
                                </form>
                                <form action="{{ url_for('delete_student', student_id=s.id) }}" method="POST" style="display:inline;" onsubmit="return confirm('Remove student from class?');">
                                    <button type="submit" class="delete-btn" style="padding: 6px 10px;">Delete</button>
                                </form>
                            </div>
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No students enrolled under this class section. Use the panel above to add students.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>"""

PRINT_RESULT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Report Card - {{ student.full_name }}</title>
    <style>
        body { font-family: 'Georgia', serif; background: #fff; color: #111; margin: 0; padding: 20px; }
        .report-card { max-width: 800px; margin: 0 auto; border: 4px double #1e3a8a; padding: 30px; position: relative; }
        .school-header { text-align: center; border-bottom: 2px solid #1e3a8a; padding-bottom: 15px; margin-bottom: 20px; }
        .school-header img { width: 70px; height: 70px; border-radius: 50%; object-fit: cover; border: 2px solid #f59e0b; margin-bottom: 8px; }
        .school-header h1 { color: #1e3a8a; font-size: 26px; margin-bottom: 4px; text-transform: uppercase; }
        .school-header p { font-size: 13px; color: #555; }
        .bio-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; background: #f8fafc; padding: 15px; border: 1px solid #cbd5e1; margin-bottom: 20px; font-size: 14px; font-family: 'Segoe UI', sans-serif; }
        .bio-item span { font-weight: bold; color: #1e3a8a; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 25px; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
        th { background: #1e3a8a; color: white; padding: 10px; text-align: center; border: 1px solid #1e3a8a; }
        td { padding: 8px 10px; border: 1px solid #cbd5e1; text-align: center; }
        td:nth-child(2) { text-align: left; }
        .summary-box { display: flex; justify-content: space-between; background: #f1f5f9; padding: 15px; border: 1px solid #cbd5e1; margin-bottom: 25px; font-family: 'Segoe UI', sans-serif; font-weight: bold; }
        .signatures { display: flex; justify-content: space-between; margin-top: 40px; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
        .sig-line { border-top: 1px solid #333; width: 220px; text-align: center; padding-top: 5px; }
        .print-btn-bar { text-align: center; margin-bottom: 20px; }
        .print-btn { background: #1e3a8a; color: white; padding: 10px 25px; font-size: 15px; border: none; border-radius: 5px; cursor: pointer; }
        @media print { .print-btn-bar { display: none; } body { padding: 0; } .report-card { border: none; padding: 0; } }
    </style>
</head>
<body>
    <div class="print-btn-bar">
        <button class="print-btn" onclick="window.print()">🖨️ Print Term Result Sheet</button>
        <a href="{{ url_for('teacher_dashboard') }}" style="margin-left: 15px; text-decoration: none; color: #1e3a8a; font-weight: bold;">Back to Dashboard</a>
    </div>

    <div class="report-card">
        <div class="school-header">
            <img src="{{ url_for('static', filename='uploads/logo.jpg') }}?t={{ range(1000,9999)|random }}" alt="School Logo" onerror="this.src='https://via.placeholder.com/70'">
            <h1>Zaria Hyfam International School</h1>
            <p>Main Campus: Zaria, Kaduna State | Excellence, Discipline & Knowledge</p>
            <h3 style="margin-top: 10px; color: #f59e0b; text-transform: uppercase; font-size: 16px;">Student Terminal Evaluation Report Card ({{ term }})</h3>
        </div>

        <div class="bio-grid">
            <div class="bio-item"><span>Student Name:</span> {{ student.full_name }}</div>
            <div class="bio-item"><span>Admission Number:</span> {{ student.admission_no }}</div>
            <div class="bio-item"><span>Class:</span> {{ student.class_name }}</div>
            <div class="bio-item"><span>Class Position:</span> <strong style="color: #d97706; font-size: 15px;">{{ position }}</strong></div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>S/N</th>
                    <th>Subject</th>
                    <th>CA1 (20)</th>
                    <th>CA2 (20)</th>
                    <th>Exam (60)</th>
                    <th>Total (100)</th>
                    <th>Grade</th>
                    <th>Remarks</th>
                </tr>
            </thead>
            <tbody>
                {% for r in records %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td>{{ r.subject }}</td>
                    <td>{{ r.ca1_score }}</td>
                    <td>{{ r.ca2_score }}</td>
                    <td>{{ r.exam_score }}</td>
                    <td><strong>{{ r.total_score }}</strong></td>
                    <td><strong>{{ r.grade }}</strong></td>
                    <td>{{ r.remarks }}</td>
                </tr>
                {% else %}
                <tr><td colspan="8" style="color: #64748b; text-align: center;">No subject evaluations recorded for this student in this term.</td></tr>
                {% endfor %}
            </tbody>
        </table>

        <div class="summary-box">
            <div>Total Cumulative Score: {{ total_score }}</div>
            <div>Class Average: {{ "%.2f"|format(class_average) }}</div>
        </div>

        <div class="signatures">
            <div class="sig-line">Form Teacher Signature</div>
            <div class="sig-line">Principal Signature & Stamp</div>
        </div>
    </div>
</body>
</html>"""

ADMIN_DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Admin Board - Zaria Hyfam</title>
    <style>
        :root {
            --primary-navy: #1e3a8a; --primary-light: #3b82f6; --accent-gold: #f59e0b;
            --success: #10b981; --danger: #ef4444; --neutral-bg: #f8fafc; --white: #ffffff;
            --text-main: #1e293b; --text-muted: #64748b; --border-color: #e2e8f0; --card-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }
        body { font-family: 'Segoe UI', sans-serif; background: var(--neutral-bg); color: var(--text-main); margin: 0; padding: 0; }
        nav { background: var(--primary-navy); display: flex; justify-content: space-between; align-items: center; padding: 15px 40px; color: white; }
        .container { max-width: 1200px; margin: 30px auto; padding: 20px; }
        .admin-meta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .meta-box { background: white; padding: 24px; border-radius: 8px; box-shadow: var(--card-shadow); border-bottom: 4px solid var(--primary-light); }
        .meta-box.gold { border-bottom-color: var(--accent-gold); }
        .meta-box h4 { font-size: 14px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 10px; }
        .meta-box p { font-size: 32px; font-weight: 800; color: var(--primary-navy); }
        .card-panel { background: white; border-radius: 8px; box-shadow: var(--card-shadow); padding: 25px; margin-bottom: 30px; }
        .table-wrapper { background: white; border-radius: 8px; box-shadow: var(--card-shadow); overflow-x: auto; margin-top: 15px; margin-bottom: 30px; }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th { background: #f1f5f9; color: var(--primary-navy); padding: 14px; }
        td { padding: 14px; border-bottom: 1px solid var(--border-color); }
        .logout-btn { color: white; background: transparent; border: 1px solid var(--danger); padding: 8px 16px; border-radius: 6px; text-decoration: none; }
        .flash { background: #d1fae5; color: #065f46; padding: 10px; border-radius: 6px; margin-bottom: 15px; }
        .submit-btn { background: var(--primary-light); color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: 600; }
        .delete-btn { background: var(--danger); color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: bold; }
        .delete-btn:hover { background: #dc2626; }
    </style>
</head>
<body>
    <nav>
        <h2>Admin Master Control Panel & Archive Vault</h2>
        <a href="{{ url_for('logout') }}" class="logout-btn">Lock Workspace</a>
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages() %}
            {% if messages %}<div class="flash">{{ messages[0] }}</div>{% endif %}
        {% endwith %}

        <div class="admin-meta-grid">
            <div class="meta-box"><h4>Registered Students</h4><p>{{ total_students }}</p></div>
            <div class="meta-box gold"><h4>Billed Revenue Portfolio</h4><p>₦{{ "{:,}".format(total_revenue) }}</p></div>
            <div class="meta-box" style="border-bottom-color: var(--success)"><h4>Archived Academic Records</h4><p>{{ total_archives }}</p></div>
        </div>

        <div class="card-panel">
            <h3 style="color: var(--primary-navy); margin-bottom: 15px; font-family: 'Georgia', serif;">School Logo Management</h3>
            <p style="font-size: 14px; color: var(--text-muted); margin-bottom: 15px;">Upload a crest or logo image (.jpg, .png) to apply it automatically across all teacher printed result report sheets.</p>
            <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 20px;">
                <img src="{{ url_for('static', filename='uploads/logo.jpg') }}?t={{ range(1000,9999)|random }}" alt="Current Logo" style="width: 70px; height: 70px; border-radius: 50%; object-fit: cover; border: 2px solid var(--accent-gold);" onerror="this.src='https://via.placeholder.com/70'">
                <form action="{{ url_for('upload_logo') }}" method="POST" enctype="multipart/form-data" style="display: flex; gap: 15px; align-items: center; flex: 1;">
                    <input type="file" name="logo_file" accept="image/*" required style="padding: 8px; background: #f8fafc; border: 1px solid var(--border-color); border-radius: 6px; flex: 1;">
                    <button type="submit" class="submit-btn">Upload & Update Logo</button>
                </form>
            </div>
        </div>

        <h3 style="color: var(--primary-navy); font-family: 'Georgia', serif; margin-top: 40px;">Historical Student Archives & Multi-Year Ledger</h3>
        <p style="font-size: 14px; color: var(--text-muted); margin-bottom: 15px;">All student profiles and terminal results are stored indefinitely here across multiple years until manually deleted by admin action.</p>
        <div class="table-wrapper">
            <table>
                <thead><tr><th>Student Full Name</th><th>Admission No</th><th>Class</th><th>Session</th><th>Term</th><th>Total Score</th><th>Action Center</th></tr></thead>
                <tbody>
                    {% for arc in archives %}
                    <tr>
                        <td><strong>{{ arc.full_name }}</strong></td>
                        <td>{{ arc.admission_no }}</td>
                        <td>{{ arc.class_name }}</td>
                        <td><span style="background: #e0f2fe; color: #0369a1; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">{{ arc.academic_year }}</span></td>
                        <td>{{ arc.term }}</td>
                        <td><strong>{{ arc.total_score }}</strong></td>
                        <td>
                            <form action="{{ url_for('delete_archive', archive_id=arc.archive_id) }}" method="POST" onsubmit="return confirm('Are you sure you want to permanently delete this student archive record?');">
                                <button type="submit" class="delete-btn">Purge Archive Record</button>
                            </form>
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No archived multi-year results logged yet. Results compiled by teachers will appear here.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <h3 style="color: var(--primary-navy); font-family: 'Georgia', serif; margin-top: 40px;">Student Admission Submissions & Profiles</h3>
        <div class="table-wrapper">
            <table>
                <thead><tr><th>Student Name</th><th>Admission No</th><th>Target Class</th><th>Parent Profile</th><th>Phone</th><th>Fee Cost</th><th>Status</th></tr></thead>
                <tbody>
                    {% for s in students %}
                    <tr>
                        <td><strong>{{ s.full_name }}</strong></td>
                        <td>{{ s.admission_no }}</td>
                        <td>{{ s.class_name }}</td>
                        <td>{{ s.parent_name or 'N/A' }} ({{ s.relation or 'Parent' }})</td>
                        <td>{{ s.phone or 'N/A' }}</td>
                        <td><strong>₦{{ "{:,}".format(s.fee or 0) }}</strong></td>
                        <td><span style="background:#f1f5f9; padding:4px 10px; border-radius:12px; font-size:12px;">Active</span></td>
                    </tr>
                    {% else %}
                    <tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No candidate enrollment profiles logged.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>"""


@app.route('/')
def index():
    return render_template_string(UNIFIED_TEMPLATE)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    portal_type = request.form.get('portal_type')

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['username'] = user['username']
        session['role'] = user['role']
        session['class_name'] = user['class_name']
        
        if user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('teacher_dashboard'))
    
    flash('Invalid credentials or access token.', 'error')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/upload_logo', methods=['POST'])
def upload_logo():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    if 'logo_file' not in request.files:
        flash('No file part selected.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    file = request.files['logo_file']
    if file.filename == '':
        flash('No selected file.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename('logo.jpg')
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash('School logo updated successfully! It will now appear on all report cards.', 'success')
    else:
        flash('Invalid image file format.', 'error')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/register_student', methods=['POST'])
def register_student():
    p_fname = request.form.get('p_fname')
    p_lname = request.form.get('p_lname')
    p_rel = request.form.get('p_rel')
    p_email = request.form.get('p_email')
    p_phone = request.form.get('p_phone')
    s_fname = request.form.get('s_fname')
    s_lname = request.form.get('s_lname')
    admission_no = request.form.get('admission_no')
    s_class = request.form.get('s_class')

    fees_structure = { "Creche": 45000, "Nursery": 55000, "Primary": 75000, "Secondary": 95000 }
    fee = fees_structure.get(s_class, 50000)

    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO students (full_name, admission_no, class_name, fee, parent_name, phone, email, relation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (f"{s_fname} {s_lname}", admission_no, s_class, fee, f"{p_fname} {p_lname}", p_phone, p_email, p_rel))
        conn.commit()
        flash('Dossier filed successfully into common storage cluster.', 'success')
    except sqlite3.IntegrityError:
        flash('Admission number already exists.', 'error')
    finally:
        conn.close()

    return redirect(url_for('index'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    conn = get_db_connection()
    students = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    total_students = len(students)
    total_revenue = sum((s['fee'] if 'fee' in s.keys() and s['fee'] is not None else 0) for s in students)
    
    archives = conn.execute("SELECT * FROM student_archives ORDER BY archive_id DESC").fetchall()
    total_archives = len(archives)
    conn.close()

    return render_template_string(ADMIN_DASHBOARD_TEMPLATE, 
                                  students=students, 
                                  total_students=total_students, 
                                  total_revenue=total_revenue, 
                                  archives=archives,
                                  total_archives=total_archives)

@app.route('/delete_archive/<int:archive_id>', methods=['POST'])
def delete_archive(archive_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    conn = get_db_connection()
    conn.execute("DELETE FROM student_archives WHERE archive_id = ?", (archive_id,))
    conn.commit()
    conn.close()
    flash('Archived student record purged successfully from historical ledger.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/teacher_dashboard')
def teacher_dashboard():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))

    class_name = session.get('class_name')
    conn = get_db_connection()
    students = conn.execute("SELECT * FROM students WHERE class_name = ?", (class_name,)).fetchall()
    
    db_subjects = conn.execute("SELECT subject_name FROM subjects WHERE class_name = ?", (class_name,)).fetchall()
    subjects = [s['subject_name'] for s in db_subjects]
    if not subjects:
        subjects = ['Mathematics', 'English Language', 'Computer Science', 'Basic Science', 'Civic Education', 'Social Studies']

    conn.close()
    return render_template_string(TEACHER_DASHBOARD_TEMPLATE, class_name=class_name, students=students, subjects=subjects)

@app.route('/add_student_direct', methods=['POST'])
def add_student_direct():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))

    class_name = session.get('class_name')
    full_name = request.form.get('full_name').strip()
    admission_no = request.form.get('admission_no').strip()
    phone = request.form.get('phone', '').strip()

    fees_structure = { "Creche": 45000, "Nursery": 55000, "Primary": 75000, "Secondary": 95000 }
    fee = fees_structure.get(class_name, 50000)

    if full_name and admission_no:
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO students (full_name, admission_no, class_name, fee, phone)
                VALUES (?, ?, ?, ?, ?)
            ''', (full_name, admission_no, class_name, fee, phone))
            conn.commit()
            flash('Student added successfully to your class section.', 'success')
        except sqlite3.IntegrityError:
            flash('Admission number already exists.', 'error')
        finally:
            conn.close()
    else:
        flash('Student full name and admission number are required.', 'error')

    return redirect(url_for('teacher_dashboard'))

@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))

    class_name = session.get('class_name')
    conn = get_db_connection()
    # Verify student belongs to teacher's class before deleting
    student = conn.execute("SELECT * FROM students WHERE id = ? AND class_name = ?", (student_id, class_name)).fetchone()
    if student:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.execute("DELETE FROM evaluations WHERE student_id = ?", (student_id,))
        conn.commit()
        flash('Student and associated evaluation records removed successfully.', 'success')
    else:
        flash('Student record not found or unauthorized.', 'error')
    conn.close()

    return redirect(url_for('teacher_dashboard'))

@app.route('/add_subject', methods=['POST'])
def add_subject():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))

    class_name = session.get('class_name')
    subject_name = request.form.get('subject_name').strip()

    if subject_name:
        conn = get_db_connection()
        existing = conn.execute("SELECT id FROM subjects WHERE class_name = ? AND subject_name = ?", (class_name, subject_name)).fetchone()
        if not existing:
            conn.execute("INSERT INTO subjects (class_name, subject_name) VALUES (?, ?)", (class_name, subject_name))
            conn.commit()
            flash('New subject added successfully to your class portfolio.', 'success')
        else:
            flash('Subject already exists for this class section.', 'error')
        conn.close()

    return redirect(url_for('teacher_dashboard'))

@app.route('/delete_subject', methods=['POST'])
def delete_subject():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))

    class_name = session.get('class_name')
    subject_name = request.form.get('subject_name')

    conn = get_db_connection()
    conn.execute("DELETE FROM subjects WHERE class_name = ? AND subject_name = ?", (class_name, subject_name))
    conn.commit()
    conn.close()
    flash('Subject removed from your class portfolio.', 'success')
    return redirect(url_for('teacher_dashboard'))

@app.route('/save_evaluation', methods=['POST'])
def save_evaluation():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))

    student_id = request.form.get('student_id')
    term = request.form.get('term')
    academic_year = request.form.get('academic_year')
    subject = request.form.get('subject')
    ca1 = float(request.form.get('ca1', 0))
    ca2 = float(request.form.get('ca2', 0))
    exam = float(request.form.get('exam', 0))
    total = ca1 + ca2 + exam
    grade, remarks = calculate_grade(total)

    conn = get_db_connection()
    existing = conn.execute("SELECT id FROM evaluations WHERE student_id = ? AND term = ? AND subject = ?", (student_id, term, subject)).fetchone()
    
    if existing:
        conn.execute("UPDATE evaluations SET ca1_score = ?, ca2_score = ?, exam_score = ?, total_score = ?, grade = ?, remarks = ? WHERE id = ?",
                     (ca1, ca2, exam, total, grade, remarks, existing['id']))
    else:
        conn.execute("INSERT INTO evaluations (student_id, term, subject, ca1_score, ca2_score, exam_score, total_score, grade, remarks) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (student_id, term, subject, ca1, ca2, exam, total, grade, remarks))

    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if student:
        all_recs = conn.execute("SELECT SUM(total_score) as cumulative FROM evaluations WHERE student_id = ? AND term = ?", (student_id, term)).fetchone()
        term_total = all_recs['cumulative'] if all_recs and all_recs['cumulative'] is not None else total

        existing_archive = conn.execute("SELECT archive_id FROM student_archives WHERE student_id = ? AND term = ? AND academic_year = ?", 
                                        (student_id, term, academic_year)).fetchone()
        if existing_archive:
            conn.execute("UPDATE student_archives SET total_score = ? WHERE archive_id = ?", (term_total, existing_archive['archive_id']))
        else:
            conn.execute("INSERT INTO student_archives (student_id, full_name, admission_no, class_name, term, academic_year, total_score, grade_summary) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (student['id'], student['full_name'], student['admission_no'], student['class_name'], term, academic_year, term_total, 'Compiled Terminal Evaluation'))

    conn.commit()
    conn.close()
    flash('Score compiled and permanently synced with the Multi-Year Admin Archive Ledger.', 'success')
    return redirect(url_for('teacher_dashboard'))

@app.route('/print_result', methods=['GET'])
def print_result():
    student_id = request.args.get('student_id')
    term = request.args.get('term', 'First Term')

    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        conn.close()
        flash('Student record not found.', 'error')
        return redirect(url_for('teacher_dashboard'))

    records = conn.execute("SELECT * FROM evaluations WHERE student_id = ? AND term = ?", (student_id, term)).fetchall()

    class_name = student['class_name']
    class_students = conn.execute("SELECT id FROM students WHERE class_name = ?", (class_name,)).fetchall()
    
    student_totals = []
    for cs in class_students:
        c_evals = conn.execute("SELECT SUM(total_score) as term_sum FROM evaluations WHERE student_id = ? AND term = ?", (cs['id'], term)).fetchone()
        t_sum = c_evals['term_sum'] if c_evals and c_evals['term_sum'] is not None else 0
        student_totals.append((cs['id'], t_sum))

    student_totals.sort(key=lambda x: x[1], reverse=True)
    
    position_str = "N/A"
    all_class_scores = [t[1] for t in student_totals if t[1] > 0]
    class_average = sum(all_class_scores) / len(all_class_scores) if all_class_scores else 0

    for idx, (s_id, score) in enumerate(student_totals, start=1):
        if s_id == int(student_id):
            if score > 0:
                position_str = ordinal_suffix(idx) + f" out of {len(class_students)}"
            break

    total_score = sum(r['total_score'] for r in records)
    conn.close()

    return render_template_string(PRINT_RESULT_TEMPLATE, 
                                  student=student, 
                                  term=term, 
                                  records=records, 
                                  total_score=total_score, 
                                  position=position_str,
                                  class_average=class_average)

if __name__ == '__main__':
    app.run(debug=True, port=5000)