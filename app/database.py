import sqlite3

DB_NAME = "automation.db"

def init_db():
    """Creates the SQLite database and table if it doesn't exist."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_text TEXT,
                days_text TEXT,
                action_text TEXT,
                is_active BOOLEAN
            )
        ''')
        conn.commit()

def save_rule(time_text: str, days_text: str, action_text: str, is_active: bool):
    """Inserts a new rule into the database and returns its unique ID."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO schedules (time_text, days_text, action_text, is_active) VALUES (?, ?, ?, ?)",
            (time_text, days_text, action_text, is_active)
        )
        conn.commit()
        return cursor.lastrowid

def get_all_rules():
    """Fetches all rules from the database as a list of dictionaries."""
    with sqlite3.connect(DB_NAME) as conn:
        # This tells SQLite to return rows as dictionaries instead of raw tuples
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM schedules")
        return [dict(row) for row in cursor.fetchall()]

def delete_rule(rule_id: int):
    """Deletes a specific rule from the database."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM schedules WHERE id = ?", (rule_id,))
        conn.commit()