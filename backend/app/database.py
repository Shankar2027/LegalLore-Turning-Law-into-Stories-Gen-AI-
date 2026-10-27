"""SQLite database for user accounts, progress tracking, and gamification badges."""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# The database file will be created in your backend folder
DB_PATH = Path("legallore_users.db")

def init_db():
    """Creates the users table if it doesn't exist yet."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                quiz_score INTEGER DEFAULT 0,
                badges TEXT DEFAULT ''
            )
        """)

@contextmanager
def get_db():
    """Safely opens and closes the database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_or_create_user(username: str) -> dict:
    """Fetches a user profile, or creates a new one starting at 0 points."""
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
        conn.commit()
        cur = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        
        return {
            "username": row["username"],
            "quiz_score": row["quiz_score"],
            "badges": row["badges"].split(",") if row["badges"] else []
        }

def update_score_and_badges(username: str, score_to_add: int) -> dict:
    """Adds quiz points and unlocks badges based on the new total."""
    with get_db() as conn:
        cur = conn.execute("SELECT quiz_score, badges FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        
        new_score = row["quiz_score"] + score_to_add
        current_badges = row["badges"].split(",") if row["badges"] else []
        
        # Badge Milestones
        new_badges_unlocked = []
        if new_score >= 3 and "Junior Paralegal" not in current_badges:
            new_badges_unlocked.append("Junior Paralegal")
        if new_score >= 10 and "Legal Eagle" not in current_badges:
            new_badges_unlocked.append("Legal Eagle")
        if new_score >= 20 and "Master Justice" not in current_badges:
            new_badges_unlocked.append("Master Justice")
            
        updated_badges_list = current_badges + new_badges_unlocked
        updated_badges_str = ",".join(updated_badges_list)
        
        conn.execute(
            "UPDATE users SET quiz_score = ?, badges = ? WHERE username = ?", 
            (new_score, updated_badges_str, username)
        )
        conn.commit()
        
        return {
            "username": username,
            "quiz_score": new_score,
            "badges": updated_badges_list,
            "new_badges_awarded": new_badges_unlocked
        }