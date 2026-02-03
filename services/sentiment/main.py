import time
import logging
import os
import feedparser
import psycopg2
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
RSS_URL = "https://cointelegraph.com/rss"

analyzer = SentimentIntensityAnalyzer()

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS market_news (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL UNIQUE,
                link TEXT,
                published_at TIMESTAMP,
                sentiment_score DECIMAL(5, 4),
                sentiment_label VARCHAR(10),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Table 'market_news' ready.")
        return True
    except Exception as e:
        logger.error(f"Init DB Error: {e}")
        return False

def analyze_and_save_news():
    logger.info("Fetching news from RSS Feed...")
    feed = feedparser.parse(RSS_URL)
    
    conn = get_db_connection()
    if not conn:
        return

    new_count = 0
    
    for entry in feed.entries:
        try:
            title = entry.title
            link = entry.link
            published_at = datetime(*entry.published_parsed[:6])

            scores = analyzer.polarity_scores(title)
            compound_score = scores['compound']
            
            if compound_score >= 0.05:
                label = "POSITIVE"
            elif compound_score <= -0.05:
                label = "NEGATIVE"
            else:
                label = "NEUTRAL"

            cur = conn.cursor()
            cur.execute("""
                INSERT INTO market_news (title, link, published_at, sentiment_score, sentiment_label)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (title) DO NOTHING
            """, (title, link, published_at, compound_score, label))
            
            if cur.rowcount > 0:
                new_count += 1
                logger.info(f"[{label}] {title[:30]}... (Score: {compound_score})")
            
            conn.commit()
            cur.close()

        except Exception as e:
            logger.error(f"Error processing entry: {e}")
            continue

    conn.close()
    if new_count == 0:
        logger.info("No new news found.")
    else:
        logger.info(f"Saved {new_count} new articles.")

if __name__ == "__main__":
    logger.info("Starting AI Sentiment Engine...")
    
    while not init_db():
        time.sleep(5)
    
    while True:
        analyze_and_save_news()
        time.sleep(900)
