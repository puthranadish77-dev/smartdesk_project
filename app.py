import os, sqlite3, random, string, requests, base64
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = "neo_brutalist_location_key"

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect("smartdesk.db")
    conn.row_factory = sqlite3.Row
    return conn

# 🔥 AUTO CREATE TABLE (CRITICAL FOR RENDER)
def init_db():
    conn = get_db()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ref_no TEXT,
        student_name TEXT,
        category TEXT,
        floor TEXT,
        room_details TEXT,
        description TEXT,
        image_path TEXT,
        status TEXT DEFAULT 'Open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

# Run DB init at startup
init_db()

# ---------------- AI IMAGE ANALYSIS ----------------
def analyze_image(image_path):
    try:
        with open(image_path, "rb") as img:
            image_bytes = img.read()

        encoded = base64.b64encode(image_bytes).decode('utf-8')

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe the issue in this image for a maintenance ticket."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded}"
                                }
                            }
                        ]
                    }
                ]
            }
        )

        result = response.json()
        return result['choices'][0]['message']['content']

    except Exception as e:
        print("AI ERROR:", e)
        return "AI could not analyze image"

# ---------------- ROUTES ----------------
@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def auth():
    session['role'] = request.form.get('role')
    session['user'] = request.form.get('username')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'role' not in session:
        return redirect(url_for('login_page'))

    conn = get_db()
    tickets = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC").fetchall()

    stats = {
        'total': len(tickets),
        'open': len([t for t in tickets if t['status'] == 'Open']),
        'resolved': len([t for t in tickets if t['status'] == 'Resolved'])
    }

    categories = [
        "Sanitary", "Plumbing", "Electric", "IT/Lab system",
        "HVAC Maintenance", "Cleanliness", "Lift", "Kiosk",
        "Fees & Registration", "Furniture", "Pest Control",
        "Lab Equipment", "Library Resources", "Security Concern",
        "Canteen Hygiene", "Event Support", "Other"
    ]

    cat_data = {c: len([t for t in tickets if t['category'] == c]) for c in categories}

    conn.close()
    return render_template('dashboard.html', tickets=tickets, stats=stats, cat_data=cat_data)

# ---------------- SUBMIT ----------------
@app.route('/submit', methods=['POST'])
def submit():
    ref = "CTS-" + ''.join(random.choices(string.digits, k=5))

    file = request.files.get('image')
    filename = ""
    ai_description = ""

    if file and file.filename != "":
        filename = f"{ref}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        ai_description = analyze_image(filepath)

    final_description = request.form.get('description')
    if not final_description or final_description.strip() == "":
        final_description = ai_description

    conn = get_db()
    conn.execute('''INSERT INTO tickets 
        (ref_no, student_name, category, floor, room_details, description, image_path) 
        VALUES (?,?,?,?,?,?,?)''',
        (ref, session['user'], request.form.get('category'),
         request.form.get('floor'), request.form.get('room_details'),
         final_description, filename))

    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))

# ---------------- AI API ----------------
@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    file = request.files.get('image')

    if not file:
        return jsonify({"error": "No image uploaded"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    result = analyze_image(filepath)

    return jsonify({"analysis": result})

# ---------------- CLOSE ----------------
@app.route('/close/<ref>')
def close_ticket(ref):
    conn = get_db()
    conn.execute("UPDATE tickets SET status='Resolved' WHERE ref_no=?", (ref,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)
