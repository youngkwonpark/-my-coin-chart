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
    index=1,  # 기본값 15분봉
)

# 업비트 데이터 가져오기 함수
@st.cache_data(ttl=10)
def get_upbit_klines(symbol, interval_minutes):
    url = f"https://api.upbit.com/v1/candles/minutes/{interval_minutes}?market={symbol}&count=200"
    headers = {"accept": "application/json"}
    
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if not isinstance(res, list):
            st.error(f"API 응답 에러: {res}")
            return [], [], [], []
    except Exception as e:
        st.error(f"네트워크 에러: {e}")
        return [], [], [], []

    res.reverse()

    candles = []
    goya_line = []
    smart_line = []
    markers = []
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

        # 고야선 (60이평)
        if len(closes) >= 60:
            goya_val = sum(closes[-60:]) / 60
            goya_line.append({"time": time_sec, "value": goya_val})

        # 스마트 라인 (20이평 임시 적용 - 추후 수식 반영 가능)
        if len(closes) >= 20:
            smart_val = sum(closes[-20:]) / 20
            smart_line.append({"time": time_sec, "value": smart_val})

    return candles, goya_line, smart_line, markers

candles, goya_data, smart_data, markers = get_upbit_klines(symbol, interval_minutes)

if candles:
    # 차트 옵션 (십자선 모드 0: 자유 이동 모드로 변경하여 부드러운 드래그 구현)
    chart_options = {
        "layout": {"background": {"type": "solid", "color": "#131722"}, "textColor": "#d1d4dc"},
        "grid": {"vertLines": {"color": "#1f2937"}, "horzLines": {"color": "#1f2937"}},
        "timeScale": {"timeVisible": True, "secondsVisible": False},
        "crosshair": {
            "mode": 0  # 0: Normal(자유 커서), 1: Magnet(봉 스냅)
        }
    }

    series = [
        {
            "type": "Candlestick", 
            "data": candles, 
            "options": {"upColor": "#26a69a", "downColor": "#ef5350"}
        },
        {
            "type": "Line", 
            "data": goya_data, 
            "options": {
                "color": "#e91e63",  # 핫핑크 / 마젠타 색상 적용
                "lineWidth": 2, 
                "title": "Goya Line (60선)"
            }
        },
        {
            "type": "Line", 
            "data": smart_data, 
            "options": {
                "color": "#fbc02d",  # 노란색 적용
                "lineWidth": 2, 
                "title": "Smart Line"
            }
        }
    ]

    renderLightweightCharts([{"chart": chart_options, "series": series}])
