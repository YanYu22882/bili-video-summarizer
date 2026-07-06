import sqlite3
from pathlib import Path

DB_PATH = Path("memory.db")

def ensure_tables():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_prefs (
        id INTEGER PRIMARY KEY,
        pref_name TEXT UNIQUE,
        pref_value TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY,
        video_name TEXT,
        note_summary TEXT,
        template_used TEXT,
        custom_prompt TEXT,
        rating INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        work_dir TEXT
    )''')
    c.execute("PRAGMA table_info(history)")
    columns = [col[1] for col in c.fetchall()]
    if 'work_dir' not in columns:
        c.execute("ALTER TABLE history ADD COLUMN work_dir TEXT")
    c.execute('''CREATE TABLE IF NOT EXISTS entity_cache (
        entity TEXT PRIMARY KEY,
        info TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def init_db():
    ensure_tables()

def get_pref(pref_name, default=None):
    ensure_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT pref_value FROM user_prefs WHERE pref_name=?", (pref_name,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def set_pref(pref_name, pref_value):
    ensure_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_prefs (pref_name, pref_value) VALUES (?, ?)", (pref_name, pref_value))
    conn.commit()
    conn.close()

def add_history(video_name, note_summary, template_used, custom_prompt, rating=None, work_dir=None):
    ensure_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if work_dir:
        c.execute("SELECT id FROM history WHERE work_dir = ?", (work_dir,))
        existing = c.fetchone()
        if existing:
            c.execute("""
                UPDATE history 
                SET video_name=?, note_summary=?, template_used=?, custom_prompt=?, rating=?, timestamp=CURRENT_TIMESTAMP
                WHERE work_dir=?
            """, (video_name, note_summary[:200], template_used, custom_prompt, rating, work_dir))
            conn.commit()
            conn.close()
            return
    c.execute("INSERT INTO history (video_name, note_summary, template_used, custom_prompt, rating, work_dir) VALUES (?, ?, ?, ?, ?, ?)",
              (video_name, note_summary[:200], template_used, custom_prompt, rating, work_dir))
    conn.commit()
    conn.close()

def get_similar_notes(video_name, limit=3):
    ensure_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    keywords = video_name.split('_')[0]
    c.execute("SELECT note_summary, template_used FROM history WHERE video_name LIKE ? ORDER BY timestamp DESC LIMIT ?", (f'%{keywords}%', limit))
    rows = c.fetchall()
    conn.close()
    return rows

def get_entity_cache(entity):
    ensure_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT info FROM entity_cache WHERE entity=?", (entity,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def set_entity_cache(entity, info):
    ensure_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO entity_cache (entity, info) VALUES (?, ?)", (entity, info))
    conn.commit()
    conn.close()

def get_all_history():
    ensure_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, video_name, note_summary, template_used, custom_prompt, rating, timestamp, work_dir
        FROM history
        ORDER BY timestamp DESC
    """)
    rows = c.fetchall()
    conn.close()
    return [{
        "id": r[0],
        "video_name": r[1],
        "summary": r[2],
        "template": r[3],
        "custom_prompt": r[4],
        "rating": r[5],
        "time": r[6],
        "work_dir": r[7]
    } for r in rows]

def delete_history_by_id(record_id):
    ensure_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM history WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

def delete_history_by_work_dir(work_dir):
    ensure_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if work_dir is None:
        c.execute("DELETE FROM history WHERE work_dir IS NULL")
    else:
        c.execute("DELETE FROM history WHERE work_dir = ?", (work_dir,))
    conn.commit()
    conn.close()