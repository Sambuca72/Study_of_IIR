import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv 
import os

load_dotenv()
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "krytoi_parser"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "")
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id SERIAL PRIMARY KEY, 
                text TEXT NOT NULL,
                author TEXT NOT NULL,
                tags TEXT,
                author_link TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        conn.commit()
        cur.close()
        conn.close()

def get_all_quotes() -> list:
    from contextlib import closing

    with closing(get_connection()) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM quotes ORDER BY created_at DESC")
            data = cur.fetchall()
            
            return [
                {
                    "id": row["id"],
                    "text": row["text"],
                    "author": row["author"],
                    "tags": row["tags"],
                    "author_link": row["author_link"],
                    "created_at": str(row["created_at"])
                } 
                for row in data]