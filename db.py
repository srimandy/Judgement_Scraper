import sqlite3
from datetime import date, timedelta

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS judgments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT,
    case_name TEXT,
    day INTEGER,
    month TEXT,
    year INTEGER,
    judgment_date TEXT, -- ISO YYYY-MM-DD
    doc_id TEXT,
    link TEXT,
    inserted_at TEXT,
    UNIQUE(doc_id, judgment_date) ON CONFLICT IGNORE
);
CREATE INDEX IF NOT EXISTS idx_judgment_date ON judgments(judgment_date);
"""

def init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.close()

def insert_records(db_path: str, records: list[dict]):
    if not records:
        return

    # Deduplicate in Python before inserting
    seen = set()
    unique_records = []
    for r in records:
        key = (r.get("doc_id"), r.get("judgment_date"))
        if key not in seen:
            seen.add(key)
            unique_records.append(r)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for r in unique_records:
        cur.execute("""
            INSERT OR IGNORE INTO judgments
            (keyword, case_name, day, month, year, judgment_date, doc_id, link, inserted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            r.get("keyword"),
            r.get("case_name"),
            r.get("day"),
            r.get("month"),
            r.get("year"),
            r.get("judgment_date"),
            r.get("doc_id"),
            r.get("link"),
        ))
    conn.commit()
    conn.close()

def get_all(db_path: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT keyword, case_name, day, month, year, judgment_date, doc_id, link
        FROM judgments
        ORDER BY judgment_date DESC
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_last_30_days(db_path: str) -> list[dict]:
    today = date.today()
    start = (today - timedelta(days=30)).isoformat()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT keyword, case_name, day, month, year, judgment_date, doc_id, link
        FROM judgments
        WHERE judgment_date IS NOT NULL AND judgment_date >= ?
        ORDER BY judgment_date DESC
    """, (start,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]