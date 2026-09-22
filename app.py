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
    ["KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP"],
    index=0,
)

# 5분, 15분, 30분, 60분, 120분 봉 설정
interval_minutes = st.sidebar.selectbox(
    "시간 봉 설정 (분)",
    [5, 15, 30, 60, 120],
    index=1,
)

# 업비트 데이터 가져오기 및 이평선 계산
@st.cache_data(ttl=10)
def get_upbit_klines(symbol, interval_minutes):
    url = f"https://api.upbit.com/v1/candles/minutes/{interval_minutes}?market={symbol}&count=200"
    headers = {"accept": "application/json"}
    
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if not isinstance(res, list):
            st.error(f"API 응답 에러: {res}")
            return [], {}
    except Exception as e:
        st.error(f"네트워크 에러: {e}")
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

        candles.append({
            "time": time_sec,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p
        })

        # 이동평균선 데이터 생성
        if len(closes) >= 5:
            ma5.append({"time": time_sec, "value": sum(closes[-5:]) / 5})
        if len(closes) >= 15:
            ma15.append({"time": time_sec, "value": sum(closes[-15:]) / 15})
        if len(closes) >= 30:
            ma30.append({"time": time_sec, "value": sum(closes[-30:]) / 30})
        if len(closes) >= 60:
            ma60.append({"time": time_sec, "value": sum(closes[-60:]) / 60})
        if len(closes) >= 120:
            ma120.append({"time": time_sec, "value": sum(closes[-120:]) / 120})

    ma_dict = {
        "ma5": ma5,
        "ma15": ma15,
        "ma30": ma30,
        "ma60": ma60,
        "ma120": ma120
    }

    return candles, ma_dict

candles, ma_dict = get_upbit_klines(symbol, interval_minutes)

if candles:
    chart_options = {
        "layout": {"background": {"type": "solid", "color": "#131722"}, "textColor": "#d1d4dc"},
        "grid": {"vertLines": {"color": "#1f2937"}, "horzLines": {"color": "#1f2937"}},
        "timeScale": {"timeVisible": True, "secondsVisible": False},
        "crosshair": {"mode": 0}  # 자유 드래그 커서 모드
    }

    series = [
        {
            "type": "Candlestick", 
            "data": candles, 
            "options": {"upColor": "#26a69a", "downColor": "#ef5350"}
        },
        {
            "type": "Line", 
            "data": ma_dict["ma5"], 
            "options": {"color": "#00e676", "lineWidth": 1, "title": "5선"}
        },
        {
            "type": "Line", 
            "data": ma_dict["ma15"], 
            "options": {"color": "#29b6f6", "lineWidth": 1, "title": "15선"}
        },
        {
            "type": "Line", 
            "data": ma_dict["ma30"], 
            "options": {"color": "#ffeb3b", "lineWidth": 1, "title": "30선"}
        },
        {
            "type": "Line", 
            "data": ma_dict["ma60"], 
            "options": {"color": "#e91e63", "lineWidth": 3, "title": "Center Line"}
        },
        {
            "type": "Line", 
            "data": ma_dict["ma120"], 
            "options": {"color": "#ab47bc", "lineWidth": 2, "title": "120선"}
        }
    ]

    renderLightweightCharts([{"chart": chart_options, "series": series}])
