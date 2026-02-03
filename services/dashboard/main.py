import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
import numpy as np
import os
import time
from datetime import timedelta

st.set_page_config(page_title="Market Sentinel", layout="wide", initial_sidebar_state="expanded")
API_URL = os.getenv("API_URL", "http://sentinel_api:8000")

TG_BOT_USERNAME = os.getenv("TG_BOT_USERNAME", "sentinel_kv_bot")

def fetch_data(endpoint):
    try:
        response = requests.get(f"{API_URL}/{endpoint}")
        return response.json() if response.status_code == 200 else []
    except: return []

st.title("Market Sentinel")
st.markdown("**Portfolio Tracker** | **Multi-Timeframe Analysis** | **AI Prediction**")
st.markdown("---")

st.sidebar.header("Portfolio Settings")
qty_btc = st.sidebar.number_input("Bitcoin (BTC)", min_value=0.0, value=0.05, step=0.01, format="%.4f")
qty_eth = st.sidebar.number_input("Ethereum (ETH)", min_value=0.0, value=2.00, step=0.1, format="%.2f")
qty_sol = st.sidebar.number_input("Solana (SOL)", min_value=0.0, value=15.00, step=1.0, format="%.2f")

MY_HOLDINGS = {
    "BTC": qty_btc,
    "ETH": qty_eth,
    "SOL": qty_sol
}

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Action")

col_btn1, col_btn2 = st.sidebar.columns(2)

with col_btn1:
    st.link_button("Bot Alert", f"https://t.me/{TG_BOT_USERNAME}", use_container_width=True)

with col_btn2:
    if st.button('Refresh', use_container_width=True):
        st.rerun()

st.subheader("My Portfolio Value")

prices = {}
total_value_usd = 0
portfolio_details = []

for symbol, quantity in MY_HOLDINGS.items():
    if quantity > 0:
        data = fetch_data(f"prices?limit=1&symbol={symbol}")
        if data:
            current_price = data[0]['price']
            holdings_value = current_price * quantity
            prices[symbol] = current_price
            total_value_usd += holdings_value
            portfolio_details.append({
                "Asset": symbol,
                "Qty": quantity,
                "Price": f"${current_price:,.2f}",
                "Value (USD)": f"${holdings_value:,.2f}"
            })

total_value_idr = total_value_usd * 16400

col_total1, col_total2 = st.columns(2)
with col_total1:
    st.metric(label="Total Net Worth (USD)", value=f"${total_value_usd:,.2f}")
with col_total2:
    st.metric(label="Estimasi Rupiah (IDR)", value=f"Rp {total_value_idr:,.0f}")

st.markdown("---")

col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("Market Analysis")
    
    c1, c2 = st.columns([1, 1])
    with c1:
        selected_asset = st.selectbox("Select Asset:", ["BTC", "ETH", "SOL"])
    with c2:
        time_options = {
            "Real-time (Last 1 Hour)": 60,
            "Last 3 Hours": 180,
            "Last 6 Hours": 360,
            "Last 12 Hours": 720,
            "Last 24 Hours": 1440,
            "Last 2 Days": 2880,
            "Last 7 Days": 10080
        }
        selected_timeframe = st.selectbox("Select Timeframe:", list(time_options.keys()))
    
    data_limit = time_options[selected_timeframe]
    price_data = fetch_data(f"prices?limit={data_limit}&symbol={selected_asset}")
    
    if price_data:
        df = pd.DataFrame(price_data)
        
        df['created_at'] = pd.to_datetime(df['created_at']) + timedelta(hours=7)
        df = df.sort_values('created_at')
        
        latest_price = df.iloc[-1]['price']
        
        df_ai_training = df.tail(60).copy()
        df_ai_training['timestamp'] = df_ai_training['created_at'].astype('int64') // 10**9
        
        X = df_ai_training[['timestamp']]
        y = df_ai_training['price']
        
        model = LinearRegression()
        model.fit(X, y)
        
        last_time = df.iloc[-1]['created_at']
        future_times = [last_time + timedelta(minutes=i) for i in range(1, 11)]
        future_timestamps = np.array([t.timestamp() for t in future_times]).reshape(-1, 1)
        future_prices = model.predict(future_timestamps)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['created_at'], y=df['price'],
            mode='lines', name='Price History',
            line=dict(color='#00CC96', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=future_times, y=future_prices,
            mode='lines', name='AI Forecast (10m)',
            line=dict(color='#FF4136', width=2, dash='dot')
        ))
        
        trend = "BULLISH" if future_prices[-1] > latest_price else "BEARISH"
        trend_color = "green" if trend == "BULLISH" else "red"
        
        st.markdown(f"### Price: ${latest_price:,.2f} <span style='color:{trend_color}; font-size:0.8em; margin-left:10px'>({trend})</span>", unsafe_allow_html=True)
        
        fig.update_layout(
            template="plotly_dark", 
            margin=dict(l=0, r=0, t=10, b=0),
            height=400,
            xaxis_title=None,
            yaxis_title=None
        )
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.info("Waiting for data ingestion...")

with col2:
    st.subheader("Global Sentiment")
    filter_opt = st.selectbox("Sentiment Filter", ["ALL", "POSITIVE", "NEGATIVE"])
    
    endpoint = "news?limit=8"
    if filter_opt != "ALL": endpoint += f"&label={filter_opt}"
        
    news_data = fetch_data(endpoint)
    
    if news_data:
        for news in news_data:
            score = news['sentiment_score']
            color = "#00CC96" if news['sentiment_label'] == "POSITIVE" else "#EF553B" if news['sentiment_label'] == "NEGATIVE" else "#B0B0B0"
            
            st.markdown(f"""
            <div style="padding: 10px; border-left: 3px solid {color}; background-color: #262730; margin-bottom: 8px; border-radius: 4px;">
                <div style="font-size: 11px; color: {color}; font-weight: bold;">{news['sentiment_label']}</div>
                <div style="margin: 4px 0;"><a href="{news['link']}" target="_blank" style="text-decoration: none; color: white; font-weight: 500; font-size: 13px;">{news['title']}</a></div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("No news data.")

time.sleep(60)
st.rerun()
