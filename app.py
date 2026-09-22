import pandas as pd
import requests
import streamlit as st
from streamlit_lightweight_charts import renderLightweightCharts

# 웹 페이지 설정
st.set_page_config(
    page_title="Crypto Chart Dashboard", page_icon="📈", layout="wide"
)

# 사이드바 설정
st.sidebar.header("⚙️ 차트 설정")
symbol_upbit = st.sidebar.selectbox(
    "업비트 코인 선택",
    ["KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP"],
    index=0,
)

# 바이낸스 심볼 매핑 (선물 USDT)
binance_symbols = {
    "KRW-BTC": "BTCUSDT",
    "KRW-ETH": "ETHUSDT",
    "KRW-SOL": "SOLUSDT",
    "KRW-XRP": "XRPUSDT"
}
symbol_binance = binance_symbols[symbol_upbit]

# 5분, 15분, 30분, 60분, 120분 봉 설정
interval_minutes = st.sidebar.selectbox(
    "시간 봉 설정 (분)",
    [5, 15, 30, 60, 120],
    index=1,
)

# 바이낸스 API 용 인터벌 매핑
binance_intervals = {
    5: "5m",
    15: "15m",
    30: "30m",
    60: "1h",
    120: "2h"
}

st.title(f"📈 {symbol_upbit} vs {symbol_binance} ({interval_minutes}분봉)")

# ---------------------------------------------------------
# 1. 업비트 데이터 가져오기 및 이평선 계산
# ---------------------------------------------------------
@st.cache_data(ttl=10)
def get_upbit_klines(symbol, interval_minutes):
    url = f"https://api.upbit.com/v1/candles/minutes/{interval_minutes}?market={symbol}&count=200"
    headers = {"accept": "application/json"}
    
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if not isinstance(res, list):
            return [], {}
    except Exception:
        return [], {}

    res.reverse()

    candles = []
    ma5, ma15, ma30, ma60, ma120 = [], [], [], [], []
    closes = []

    for item in res:
        time_sec = int(item["timestamp"] / 1000)
        open_p = float(item["opening_price"])
        high_p = float(item["high_price"])
        low_p = float(item["low_price"])
        close_p = float(item["trade_price"])

        closes.append(close_p)
        candles.append({"time": time_sec, "open": open_p, "high": high_p, "low": low_p, "close": close_p})

        if len(closes) >= 5: ma5.append({"time": time_sec, "value": sum(closes[-5:]) / 5})
        if len(closes) >= 15: ma15.append({"time": time_sec, "value": sum(closes[-15:]) / 15})
        if len(closes) >= 30: ma30.append({"time": time_sec, "value": sum(closes[-30:]) / 30})
        if len(closes) >= 60: ma60.append({"time": time_sec, "value": sum(closes[-60:]) / 60})
        if len(closes) >= 120: ma120.append({"time": time_sec, "value": sum(closes[-120:]) / 120})

    return candles, {"ma5": ma5, "ma15": ma15, "ma30": ma30, "ma60": ma60, "ma120": ma120}

# ---------------------------------------------------------
# 2. 바이낸스 선물(Futures) 데이터 가져오기 및 이평선 계산
# ---------------------------------------------------------
@st.cache_data(ttl=10)
def get_binance_klines(symbol, interval_minutes):
    interval_str = binance_intervals.get(interval_minutes, "15m")
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval_str}&limit=200"
    
    try:
        res = requests.get(url, timeout=5).json()
        if not isinstance(res, list):
            return [], {}
    except Exception:
        return [], {}

    candles = []
    ma5, ma15, ma30, ma60, ma120 = [], [], [], [], []
    closes = []

    for item in res:
        time_sec = int(item[0] / 1000)
        open_p = float(item[1])
        high_p = float(item[2])
        low_p = float(item[3])
        close_p = float(item[4])

        closes.append(close_p)
        candles.append({"time": time_sec, "open": open_p, "high": high_p, "low": low_p, "close": close_p})

        if len(closes) >= 5: ma5.append({"time": time_sec, "value": sum(closes[-5:]) / 5})
        if len(closes) >= 15: ma15.append({"time": time_sec, "value": sum(closes[-15:]) / 15})
        if len(closes) >= 30: ma30.append({"time": time_sec, "value": sum(closes[-30:]) / 30})
        if len(closes) >= 60: ma60.append({"time": time_sec, "value": sum(closes[-60:]) / 60})
        if len(closes) >= 120: ma120.append({"time": time_sec, "value": sum(closes[-120:]) / 120})

    return candles, {"ma5": ma5, "ma15": ma15, "ma30": ma30, "ma60": ma60, "ma120": ma120}

# 공통 차트 옵션 생성 함수
def build_chart_config(candles, ma_dict, title_name):
    chart_options = {
        "height": 500,
        "layout": {"background": {"type": "solid", "color": "#131722"}, "textColor": "#d1d4dc"},
        "grid": {"vertLines": {"color": "#1f2937"}, "horzLines": {"color": "#1f2937"}},
        "timeScale": {"timeVisible": True, "secondsVisible": False},
        "crosshair": {"mode": 0}
    }

    series = [
        {"type": "Candlestick", "data": candles, "options": {"upColor": "#26a69a", "downColor": "#ef5350"}},
        {"type": "Line", "data": ma_dict["ma5"], "options": {"color": "#00e676", "lineWidth": 1, "title": "5선"}},
        {"type": "Line", "data": ma_dict["ma15"], "options": {"color": "#29b6f6", "lineWidth": 1, "title": "15선"}},
        {"type": "Line", "data": ma_dict["ma30"], "options": {"color": "#ffeb3b", "lineWidth": 1, "title": "30선"}},
        {"type": "Line", "data": ma_dict["ma60"], "options": {"color": "#e91e63", "lineWidth": 3, "title": "Center Line"}},
        {"type": "Line", "data": ma_dict["ma120"], "options": {"color": "#ab47bc", "lineWidth": 2, "title": "120선"}}
    ]

    return {"chart": chart_options, "series": series}

# 데이터 수집 및 차트 출력
upbit_candles, upbit_mas = get_upbit_klines(symbol_upbit, interval_minutes)
binance_candles, binance_mas = get_binance_klines(symbol_binance, interval_minutes)

st.subheader(f"🇰🇷 업비트 ({symbol_upbit})")
if upbit_candles:
    renderLightweightCharts([build_chart_config(upbit_candles, upbit_mas, symbol_upbit)])

st.subheader(f"🌐 바이낸스 선물 ({symbol_binance})")
if binance_candles:
    renderLightweightCharts([build_chart_config(binance_candles, binance_mas, symbol_binance)])
