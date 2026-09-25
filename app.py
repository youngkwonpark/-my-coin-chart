import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(
    page_title="고야 스마트 프리미엄 차트",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ 고야 스마트 프리미엄 차트 (Pro Signal v3.3)")

# 사용자 입력 사이드바 또는 상단 입력창
col1, col2 = st.columns([2, 1])
with col1:
    symbol = st.text_input("코인 심볼 입력 (예: XRPUSDT, BTCUSDT)", value="XRPUSDT").upper().strip()
with col2:
    interval = st.selectbox("시간봉 선택", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3)

@st.cache_data(ttl=60)
def fetch_binance_data(symbol, interval):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": 100
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code != 200:
            return None
        data = response.json()
        if not isinstance(data, list) or len(data) == 0:
            return None
            
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
            
        return df
    except Exception as e:
        return None

# 데이터 불러오기
df = fetch_binance_data(symbol, interval)

if df is not None and not df.empty:
    st.success(f"성공적으로 {symbol} ({interval}) 데이터를 불러왔습니다!")
    
    # Plotly 캔들스틱 차트 생성
    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=symbol
    )])
    
    fig.update_layout(
        title=f"{symbol} Price Chart",
        yaxis_title="USDT",
        xaxis_rangeslider_visible=False,
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("코인 데이터를 불러오지 못했습니다. 심볼명을 다시 확인해 주세요.")
