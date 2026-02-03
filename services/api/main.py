import os
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from psycopg2.extras import RealDictCursor

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

app = FastAPI(title="Market Sentinel API", version="2.0.0")

class CryptoPriceResponse(BaseModel):
    id: int
    symbol: str
    price: float
    created_at: datetime

class NewsSentimentResponse(BaseModel):
    id: int
    title: str
    link: str
    published_at: datetime
    sentiment_score: float
    sentiment_label: str

def get_db_connection():
    try:
        return psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS,
            cursor_factory=RealDictCursor
        )
    except Exception as e:
        print(f"DB Error: {e}")
        return None

@app.get("/")
def health_check():
    return {"status": "active", "version": "2.0.0 (Multi-Asset)"}

@app.get("/prices", response_model=List[CryptoPriceResponse])
def get_latest_prices(limit: int = 50, symbol: Optional[str] = None):
    conn = get_db_connection()
    if not conn: raise HTTPException(500, "DB Error")
    
    try:
        cur = conn.cursor()
        
        if symbol:
            query = """
                SELECT id, symbol, price, created_at 
                FROM crypto_prices 
                WHERE symbol = %s 
                ORDER BY created_at DESC LIMIT %s
            """
            cur.execute(query, (symbol.upper(), limit))
        else:
            query = """
                SELECT id, symbol, price, created_at 
                FROM crypto_prices 
                ORDER BY created_at DESC LIMIT %s
            """
            cur.execute(query, (limit,))
            
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        if conn: conn.close()
        raise HTTPException(500, str(e))

@app.get("/news", response_model=List[NewsSentimentResponse])
def get_market_news(limit: int = 10, label: Optional[str] = None):
    conn = get_db_connection()
    if not conn: raise HTTPException(500, "DB Error")
    try:
        cur = conn.cursor()
        if label:
            query = "SELECT * FROM market_news WHERE sentiment_label = %s ORDER BY published_at DESC LIMIT %s"
            cur.execute(query, (label.upper(), limit))
        else:
            query = "SELECT * FROM market_news ORDER BY published_at DESC LIMIT %s"
            cur.execute(query, (limit,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        if conn: conn.close()
        raise HTTPException(500, str(e))
