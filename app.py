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
    res = requests.get(url).json()

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

        candles.append(
            {
                "time": time_sec,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
            }
        )

        # 고야선 (60이평)
        if len(closes) >= 60:
            goya_val = sum(closes[-60:]) / 60
            goya_line.append({"time": time_sec, "value": goya_val})

            # 시그널 마커
            prev_close = closes[-2]
            prev_goya = sum(closes[-61:-1]) / 60
            if prev_close <= prev_goya and close_p > goya_val:
                markers.append(
                    {
                        "time": time_sec,
                        "position": "belowBar",
                        "color": "#26a69a",
                        "shape": "arrowUp",
                        "text": "LONG",
                    }
                )
            elif prev_close >= prev_goya and close_p < goya_val:
                markers.append(
                    {
                        "time": time_sec,
                        "position": "aboveBar",
                        "color": "#ef5350",
                        "shape": "arrowDown",
                        "text": "SHORT",
                    }
                )

        # 스마트 라인 (20이평)
        if len(closes) >= 20:
            smart_val = sum(closes[-20:]) / 20
            smart_line.append({"time": time_sec, "value": smart_val})

    return candles, goya_line, smart_line, markers


candles, goya_data, smart_data, markers = get_binance_klines(symbol, interval)

# 차트 옵션 설정
chart_options = {
    "width": 1000,
    "height": 600,
    "layout": {
        "backgroundColor": "#121212",
        "textColor": "#E0E0E0",
    },
    "grid": {
        "vertLines": {"color": "#1F2937"},
        "horzLines": {"color": "#1F2937"},
    },
    "crosshair": {"mode": 0},
    "priceScale": {"borderColor": "#374151"},
    "timeScale": {"borderColor": "#374151", "timeVisible": True},
}

series_list = [
    {
        "type": "Candlestick",
        "data": candles,
        "options": {
            "upColor": "#26a69a",
            "downColor": "#ef5350",
            "borderVisible": False,
            "wickUpColor": "#26a69a",
            "wickDownColor": "#ef5350",
        },
        "markers": markers,
    },
    {
        "type": "Line",
        "data": goya_data,
        "options": {
            "color": "#FF4081",
            "lineWidth": 2,
            "title": "GOYA LINE",
        },
    },
    {
        "type": "Line",
        "data": smart_data,
        "options": {
            "color": "#FFD54F",
            "lineWidth": 2,
            "title": "Smart Line",
        },
    },
]

# 차트 렌더링
renderLightweightCharts([{"chart": chart_options, "series": series_list}])
