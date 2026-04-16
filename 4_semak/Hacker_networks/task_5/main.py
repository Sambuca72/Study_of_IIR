from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, get_all_quotes
from parser import parse_quotes


app = FastAPI(
    title="Quotes Parser",
    description="Парсинг цитат и сохранения в БД(PostgreSQL)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[""],
    allow_methods=[""],
    allow_headers=[""],
)

@app.on_event("startup")
def startup_event():
    init_db()

# Запуск сервера
@app.get("/parse")
def start_parsing(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="Параметр 'url' обязателен")
    
    result = parse_quotes(url)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result

# Получение данных из БД
@app.get("/get_data")
def get_data():
    try:
        data = get_all_quotes()
        return {
            "status": "success",
            "count": len(data),
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def root():
    return {
        "message": "Парсер цитат",
        "endpoints": {
            "parse": "/parse?url=https://quotes.toscrape.com/login",
            "get_data": "/get_data"
        }
    }

#curl "http://127.0.0.1:8000/parse?url=https://quotes.toscrape.com"
# curl "http://127.0.0.1:8000/get_data"