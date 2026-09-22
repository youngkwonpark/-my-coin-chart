import pandas as pd
import requests
import streamlit as st
from streamlit_lightweight_charts import renderLightweightCharts

# 웹 페이지 설정
st.set_page_config(
    page_title="Crypto Chart Dashboard", page_icon="📈", layout="wide"
)

st.title("📈 실시간 코인 차트 대시보드")

# 사이드바 설정
st.sidebar.header("⚙️ 차트 설정")
symbol = st.sidebar.selectbox(
    "코인 선택",
    ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ZECUSDT"],
    index=0,
)

interval = st.sidebar.selectbox(
    "시간 봉 설정",
    ["1m", "5m", "15m", "1h", "4h", "1d"],
    index=3,
)

# 데이터 가져오기 함수
@st.cache_data(ttl=10)
def get_binance_klines(symbol, interval):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=200"
    try:
        res = requests.get(url, timeout=5).json()
        if not isinstance(res, list):
            st.error(f"API 응답 에러: {res}")
            return [], [], [], []
    except Exception as e:
        st.error(f"네트워크 에러: {e}")
        return [], [], [], []

    candles = []
    goya_line = []
    smart_line = []
    markers = []
    closes = []

    for item in res:
        time_sec = int(item[0] / 1000)
        open_p = float(item[1])
        high_p = float(item[2])
        low_p = float(item[3])
        close_p = float(item[4])

        closes.append(close_p)

        candles.append({
            "time": time_sec,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p
        })

        # 고야선 (60이평)
        if len(closes) >= 60:
            goya_val = sum(closes[-60:]) / 60
            goya_line.append({"time": time_sec, "value": goya_val})

        # 스마트 라인 (20이평)
        if len(closes) >= 20:
            smart_val = sum(closes[-20:]) / 20
            smart_line.append({"time": time_sec, "value": smart_val})

        # 시그널 조건 (20이평 돌파 예시)
        if len(closes) >= 21:
            prev_close = closes[-2]
            prev_smart = sum(closes[-21:-1]) / 20
            curr_smart = smart_val

            if prev_close <= prev_smart and close_p > curr_smart:
                markers.append({
                    "time": time_sec,
                    "position": "belowBar",
                    "color": "#26a69a",
                    "shape": "arrowUp",
                    "text": "BUY"
                })
            elif prev_close >= prev_smart and close_p < curr_smart:
                markers.append({
                    "time": time_sec,
                    "position": "aboveBar",
                    "color": "#ef5350",
                    "shape": "arrowDown",
                    "text": "SELL"
                })

    return candles, goya_line, smart_line, markers

candles, goya_data, smart_data, markers = get_binance_klines(symbol, interval)

if candles:
    chart_options = {
        "layout": {"background": {"type": "solid", "color": "#131722"}, "textColor": "#d1d4dc"},
        "grid": {"vertLines": {"color": "#1f2937"}, "horzLines": {"color": "#1f2937"}},
        "timeScale": {"timeVisible": True, "secondsVisible": False}
    }

    series = [
        {"type": "Candlestick", "data": candles, "options": {"upColor": "#26a69a", "downColor": "#ef5350"}},
        {"type": "Line", "data": goya_data, "options": {"color": "#ff9800", "lineWidth": 2, "title": "60 MA (고야선)"}},
        {"type": "Line", "data": smart_data, "options": {"color": "#2196f3", "lineWidth": 2, "title": "20 MA (스마트 라인)"}}
    ]

    renderLightweightCharts([{"chart": chart_options, "series": series}])
