from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database setup
conn = sqlite3.connect('notes.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, code TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, date TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS note_entries (id INTEGER PRIMARY KEY, note_id INTEGER, date TEXT, topic TEXT, description TEXT, price REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY, user_id INTEGER, topic TEXT, reminder_date TEXT, created_at TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY, user_id INTEGER, message TEXT, type TEXT, created_at TEXT, is_read INTEGER DEFAULT 0)''')
conn.commit()
conn.close()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        code = request.form['code']
        conn = sqlite3.connect('notes.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE code=?', (code,))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            return redirect(url_for('home'))
        flash("Invalid code")
    return render_template('login.html')

def add_notification(user_id, message, notification_type):
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO notifications (user_id, message, type, created_at) VALUES (?, ?, ?, ?)',
              (user_id, message, notification_type, created_at))
    conn.commit()
    conn.close()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        code = request.form['code']
        conn = sqlite3.connect('notes.db')
        c = conn.cursor()
        c.execute('INSERT INTO users (name, code) VALUES (?, ?)', (name, code))
        conn.commit()
        conn.close()
        flash("Account created. Login now.")
        add_notification(c.lastrowid, "Welcome to Farm Manager! Your account has been successfully created.", "alert")
        add_notification(c.lastrowid, "Don't forget to check the weather forecast for optimal planting conditions today!", "weather")
        add_notification(c.lastrowid, "Reminder: Your irrigation system needs maintenance next week.", "farming")
        add_notification(c.lastrowid, "New research indicates advanced fertilizers can boost your yield by 15% this season!", "farming")
        add_notification(c.lastrowid, "Government announces new agricultural subsidies. Check details on our schemes page!", "alert")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute('SELECT topic FROM reminders WHERE user_id=? AND reminder_date=?', (session['user_id'], today))
    reminders = c.fetchall()
    conn.close()
    return render_template('home.html', reminders=reminders)

@app.route('/notifications')
def get_notifications():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute('SELECT id, message, type, created_at, is_read FROM notifications WHERE user_id=? ORDER BY created_at DESC', (user_id,))
    notifications = c.fetchall()
    conn.close()
    
    # Convert to a list of dicts for easier JSON serialization
    notifications_list = []
    for notif in notifications:
        notifications_list.append({
            'id': notif[0],
            'message': notif[1],
            'type': notif[2],
            'created_at': notif[3],
            'is_read': bool(notif[4])
        })
    
    return jsonify(notifications_list)

@app.route('/notifications_page')
def notifications_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute('SELECT id, message, type, created_at, is_read FROM notifications WHERE user_id=? ORDER BY created_at DESC', (user_id,))
    notifications = c.fetchall()
    conn.close()
    
    notifications_list = []
    for notif in notifications:
        notifications_list.append({
            'id': notif[0],
            'message': notif[1],
            'type': notif[2],
            'created_at': notif[3],
            'is_read': bool(notif[4])
        })
    
    return render_template('notifications.html', notifications=notifications_list)

@app.route('/notifications/mark_read/<int:notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute('UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?', (notification_id, session['user_id']))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Notification marked as read'})

@app.route('/notifications/mark_all_read', methods=['POST'])
def mark_all_notifications_read():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute('UPDATE notifications SET is_read=1 WHERE user_id=?', (user_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'All notifications marked as read'})

@app.route('/notes')
def notes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute('SELECT * FROM notes WHERE user_id=?', (session['user_id'],))
    notes = c.fetchall()
    conn.close()
    return render_template('notes.html', notes=notes)

@app.route('/create_note', methods=['POST'])
def create_note():
    title = request.form['title']
    date = datetime.now().strftime("%A, %d %B %Y")
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute('INSERT INTO notes (user_id, title, date) VALUES (?, ?, ?)', (session['user_id'], title, date))
    
    # Get the ID of the newly created note
    note_id = c.lastrowid
    
    conn.commit()
    conn.close()
    
    # Redirect directly to the newly created note instead of notes list
    flash("New note created successfully! Start adding your farming entries.")
    return redirect(url_for('view_note', note_id=note_id))

@app.route('/note/<int:note_id>', methods=['GET', 'POST'])
def view_note(note_id):
    now = datetime.now()
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    if request.method == 'POST':
        if 'day' in request.form and 'month' in request.form and 'year' in request.form:
            day = int(request.form['day'])
            month = int(request.form['month'])
            year = int(request.form['year'])
            date = datetime(year, month, day).strftime("%A, %d %B %Y")
        else:
            date = datetime.now().strftime("%A, %d %B %Y")
        topic = request.form['topic']
        desc = request.form['desc']
        price = float(request.form['price'] or 0)
        c.execute('INSERT INTO note_entries (note_id, date, topic, description, price) VALUES (?, ?, ?, ?, ?)',
                  (note_id, date, topic, desc, price))
        conn.commit()
        flash("Entry added. Remember to save before exiting.")
    c.execute('SELECT title FROM notes WHERE id=?', (note_id,))
    title = c.fetchone()[0]
    c.execute('SELECT * FROM note_entries WHERE note_id=?', (note_id,))
    entries = c.fetchall()
    total = sum([entry[5] for entry in entries])
    conn.close()
    return render_template(
        'view_note.html',
        entries=entries,
        title=title,
        note_id=note_id,
        total=total,
        current_day=now.day,
        current_month=now.month,
        current_year=now.year
    )

@app.route('/bulk_delete_entries/<int:note_id>', methods=['POST'])
def bulk_delete_entries(note_id):
    entry_ids = request.form.getlist('entry_ids')
    if entry_ids:
        conn = sqlite3.connect('notes.db')
        c = conn.cursor()
        # Delete multiple entries at once
        placeholders = ','.join('?' * len(entry_ids))
        c.execute(f'DELETE FROM note_entries WHERE id IN ({placeholders})', entry_ids)
        conn.commit()
        conn.close()
        flash(f"{len(entry_ids)} entries deleted successfully.")
    else:
        flash("No entries selected for deletion.")
    return redirect(url_for('view_note', note_id=note_id))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/set_reminder', methods=['GET', 'POST'])
def set_reminder():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        topic = request.form['topic']
        reminder_date_str = request.form['reminder_date']
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect('notes.db')
        c = conn.cursor()
        c.execute('INSERT INTO reminders (user_id, topic, reminder_date, created_at) VALUES (?, ?, ?, ?)',
                  (session['user_id'], topic, reminder_date_str, created_at))
        conn.commit()
        conn.close()
        flash("Reminder set successfully!")
        add_notification(session['user_id'], f"New reminder set for: {topic} on {reminder_date_str}.", "farming")
        return redirect(url_for('home'))
    
    return render_template('reminders.html')

if __name__ == '__main__':
    app.run()
