import sqlite3
import os

DB_FILE = "agent_state.db"

def init_db():
    """Initialize the SQLite database and create tables."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_state (
            session_id TEXT PRIMARY KEY,
            state_json TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_state(session_id: str, state_json: str):
    """Save or update the agent state for a session."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO agent_state (session_id, state_json)
        VALUES (?, ?)
        ON CONFLICT(session_id) DO UPDATE SET state_json=excluded.state_json
    """, (session_id, state_json))
    conn.commit()
    conn.close()


def load_state(session_id: str):
    """Load the agent state for a given session."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT state_json FROM agent_state WHERE session_id = ?
    """, (session_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None


def clear_state(session_id: str):
    """Delete a session's state (optional cleanup)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM agent_state WHERE session_id = ?
    """, (session_id,))
    conn.commit()
    conn.close()
