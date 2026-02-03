import os
import time
import logging
import requests
import psycopg2

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
WATCH_LIST = os.getenv("WATCH_LIST", "bitcoin,ethereum,solana")

SYMBOL_MAP = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL"}

TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DROP_MARGIN = float(os.getenv("DROP_MARGIN"))

high_water_mark = {}

low_water_mark = {}

def get_db_connection():
    try:
        return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS crypto_prices (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            price DECIMAL(15, 2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()
        conn.close()
        return True
    except Exception: return False

def check_smart_alert(symbol, current_price):
    global high_water_mark, low_water_mark
    
    if symbol not in high_water_mark: high_water_mark[symbol] = current_price
    if symbol not in low_water_mark: low_water_mark[symbol] = current_price

    margin = DROP_MARGIN
    if symbol == "ETH": margin = DROP_MARGIN / 10
    if symbol == "SOL": margin = DROP_MARGIN / 100

    highest = high_water_mark[symbol]
    if current_price > highest:
        high_water_mark[symbol] = current_price
        if current_price - (margin * 2) > low_water_mark[symbol]:
             low_water_mark[symbol] = current_price - (margin * 2)

    dump_threshold = high_water_mark[symbol] - margin
    if current_price < dump_threshold:
        send_telegram(symbol, "📉 DUMP/CRASH", current_price, high_water_mark[symbol], dump_threshold)
        high_water_mark[symbol] = current_price 
        logger.info(f"Reset High Mark for {symbol}")

    lowest = low_water_mark[symbol]
    if current_price < lowest:
        low_water_mark[symbol] = current_price
        if current_price + (margin * 2) < high_water_mark[symbol]:
             high_water_mark[symbol] = current_price + (margin * 2)

    pump_threshold = low_water_mark[symbol] + margin
    if current_price > pump_threshold:
        send_telegram(symbol, "🚀 PUMP/MOON", current_price, low_water_mark[symbol], pump_threshold)
        low_water_mark[symbol] = current_price 
        logger.info(f"Reset Low Mark for {symbol}")

def send_telegram(symbol, type_alert, current, ref_price, threshold):
    if not TG_TOKEN or not TG_CHAT_ID: return
    
    emoji = "🔴" if "DUMP" in type_alert else "🟢"
    action = "Price dropped from High" if "DUMP" in type_alert else "Price bounced from Low"
    
    diff = abs(current - ref_price)
    
    msg = (
        f"{emoji} **{symbol} {type_alert} ALERT**\n\n"
        f"{action}\n"
        f"💵 **Current:** ${current:,.2f}\n"
        f"⚓ **Ref Point:** ${ref_price:,.2f}\n"
        f"↕️ **Diff:** ${diff:,.2f}\n"
        f"(Trigger limit was ${threshold:,.0f})"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        )
        logger.info(f"Alert {type_alert} sent for {symbol}")
    except Exception: pass

def fetch_and_save():
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={WATCH_LIST}&vs_currencies=usd"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        conn = get_db_connection()
        if not conn: return
        cur = conn.cursor()
        
        for coin_id, values in data.items():
            price = float(values['usd'])
            symbol = SYMBOL_MAP.get(coin_id, coin_id.upper())
            
            cur.execute("INSERT INTO crypto_prices (symbol, price) VALUES (%s, %s)", (symbol, price))
            logger.info(f"Saved: {symbol} = ${price}")
            
            check_smart_alert(symbol, price)

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"Process Error: {e}")

def main():
    logger.info("Starting Smart Trailing Alert System...")
    while True:
        if init_db(): break
        time.sleep(5)

    while True:
        fetch_and_save()
        time.sleep(60)

if __name__ == "__main__":
    main()
