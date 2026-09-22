import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
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

# 바이낸스 선물 심볼 매핑
binance_symbols = {
    "KRW-BTC": "BINANCE:BTCUSDT.P",
    "KRW-ETH": "BINANCE:ETHUSDT.P",
    "KRW-SOL": "BINANCE:SOLUSDT.P",
    "KRW-XRP": "BINANCE:XRPUSDT.P"
}
symbol_binance_tv = binance_symbols[symbol_upbit]

# 5분, 15분, 30분, 60분, 120분 봉 설정
interval_minutes = st.sidebar.selectbox(
    "시간 봉 설정 (분)",
    [5, 15, 30, 60, 120],
    index=1,
)

# 트레이딩뷰 인터벌 매핑
tv_intervals = {
    5: "5",
    15: "15",
    30: "30",
    60: "60",
    120: "120"
}

st.title(f"📈 {symbol_upbit} vs {symbol_binance_tv.split(':')[1]} ({interval_minutes}분봉)")

# ---------------------------------------------------------
# 1. 상단: 업비트 차트 (Lightweight Charts)
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

def build_chart_config(candles, ma_dict):
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

upbit_candles, upbit_mas = get_upbit_klines(symbol_upbit, interval_minutes)

st.subheader(f"🇰🇷 업비트 ({symbol_upbit})")
if upbit_candles:
    renderLightweightCharts([build_chart_config(upbit_candles, upbit_mas)], key="upbit_chart")

# ---------------------------------------------------------
# 2. 하단: 바이낸스 실시간 차트 (TradingView 공식 위젯)
# ---------------------------------------------------------
st.subheader(f"🌐 바이낸스 선물 실시간 ({symbol_binance_tv.split(':')[1]})")

tv_interval = tv_intervals.get(interval_minutes, "15")

tradingview_html = f"""
<!-- TradingView Widget BEGIN -->
<div class="tradingview-widget-container" style="height:500px;width:100%;">
  <div id="tradingview_binance" style="height:500px;width:100%;"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget({{
    "autosize": true,
    "symbol": "{symbol_binance_tv}",
    "interval": "{tv_interval}",
    "timezone": "Asia/Seoul",
    "theme": "dark",
    "style": "1",
    "locale": "kr",
    "toolbar_bg": "#f1f3f6",
    "enable_publishing": false,
    "hide_side_toolbar": false,
    "allow_symbol_change": false,
    "container_id": "tradingview_binance"
  }});
  </script>
</div>
<!-- TradingView Widget END -->
"""

components.html(tradingview_html, height=505)
