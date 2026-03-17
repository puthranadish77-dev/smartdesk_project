import sqlite3

conn = sqlite3.connect("smartdesk.db")

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

print("Database created successfully.")