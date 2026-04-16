import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv 
import os
import time


load_dotenv()
def get_connection():
    db_host = os.getenv("DB_HOST", "database")
    db_port = int(os.getenv("DB_PORT", 5432))
    db_name = os.getenv("DB_NAME", "krytoi_parser")
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASSWORD", "popka228")

    retries = 10
    while retries > 0:
        try:
            return psycopg2.connect(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_pass
            )
        except psycopg2.OperationalError:
            retries -= 1
            print(f"База данных еще недоступна. Ждем... : {retries}")
            time.sleep(3)
    
    raise Exception("Не удалось подключиться к базе данных")

def init_db():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS quotes (
                        id SERIAL PRIMARY KEY, 
                        text TEXT NOT NULL,
                        author TEXT NOT NULL,
                        tags TEXT,
                        author_link TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
                conn.commit()
    except Exception as e:
        print(f"Ошибка при инициализации БД: {e}")

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