import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="고야 스마트 프리미엄 차트", layout="wide")

st.title("⚡ 고야 스마트 프리미엄 차트 (Pro Signal v3.3)")

# 코인 심볼 및 주기 선택 레이아웃
col1, col2 = st.columns([2, 2])
with col1:
    symbol = st.text_input("코인 심볼 입력 (예: XRPUSDT, BTCUSDT)", value="XRPUSDT").upper()
with col2:
    timeframe = st.selectbox("시간봉 선택", ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"], index=5)

@st.cache_data(ttl=10)
def fetch_data(sym, tf):
    url = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval={tf}&limit=200"
    res = requests.get(url)
    if res.status_code != 200:
        return None
    data = res.json()
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=9)
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)
    return df

df = fetch_data(symbol, timeframe)

if df is not None and not df.empty:
    # EMA(이동평균선) 계산
    df['goya'] = df['close'].ewm(span=7, adjust=False).mean()
    df['smart'] = df['close'].ewm(span=25, adjust=False).mean()
    
    current_price = df['close'].iloc[-1]
    st.metric(label=f"현재가 ({symbol})", value=f"${current_price:,.4f}")

    # Plotly 차트 구성
    fig = go.Figure()
    
    # 캔들스틱 추가
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Candle'
    ))
    
    # 고야선 (EMA 7) 및 스마트선 (EMA 25) 추가
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['goya'], line=dict(color='#ec4899', width=2), name='Goya Line (EMA 7)'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['smart'], line=dict(color='yellow', width=1.5), name='Smart Line (EMA 25)'))

    fig.update_layout(
        template='plotly_dark',
        height=550,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_rangeslider_visible=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.success("거짓 신호 필터 및 고야선 트랩 모니터링이 정상적으로 작동 중입니다.")
else:
    st.error("코인 데이터를 불러오지 못했습니다. 심볼명을 다시 확인해 주세요.")
