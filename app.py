import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit_lightweight_charts import renderLightweightCharts

# 웹 페이지 설정
st.set_page_config(
    page_title="Crypto Chart Dashboard", page_icon="📈", layout="wide"
)

# 사이드바 설정 (코인 선택)
st.sidebar.header("⚙️ 코인 선택")
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

# 세션 상태에 선택된 시간 봉 저장 (기본값: 15분)
if "selected_tf" not in st.session_state:
    st.session_state.selected_tf = "15분"

# 시간 봉 옵션
tf_list = [
    "1분", "3분", "5분", "10분", "15분", "30분", "45분",
    "1시간", "2시간", "4시간", "6시간", "8시간", "10시간", "12시간"
]

timeframe_to_minutes = {
    "1분": 1, "3분": 3, "5분": 5, "10분": 10, "15분": 15, "30분": 30, "45분": 45,
    "1시간": 60, "2시간": 120, "4시간": 240, "6시간": 360, "8시간": 480, "10시간": 600, "12시간": 720
}

tv_intervals = {
    1: "1", 3: "3", 5: "5", 10: "10", 15: "15", 30: "30", 45: "45",
    60: "60", 120: "120", 240: "240", 360: "360", 480: "480", 600: "720", 720: "720"
}

st.title(f"📈 {symbol_upbit} vs {symbol_binance_tv.split(':')[1]}")

# ---------------------------------------------------------
# 상단 시간 봉 클릭 버튼 레이아웃 (바이낸스 스타일)
# ---------------------------------------------------------
st.write("⏱️ **시간 봉 선택**")
cols = st.columns(len(tf_list))

for i, tf in enumerate(tf_list):
    # 현재 선택된 버튼은 강조 표시
    button_label = f"[{tf}]" if st.session_state.selected_tf == tf else tf
    if cols[i].button(button_label, key=f"tf_btn_{tf}", use_container_width=True):
        st.session_state.selected_tf = tf
        st.rerun()

current_tf = st.session_state.selected_tf
target_minutes = timeframe_to_minutes[current_tf]

st.markdown(f"**현재 설정:** `<{current_tf}>` 봉 차트", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. 상단: 업비트 차트
# ---------------------------------------------------------
@st.cache_data(ttl=10)
def get_upbit_klines(symbol, minutes):
    upbit_native_minutes = [1, 3, 5, 10, 15, 30, 45, 60, 240]
    
    if minutes in upbit_native_minutes:
        fetch_minutes = minutes
        fetch_count = 200
    else:
        fetch_minutes = 60
        fetch_count = min(200 * (minutes // 60), 200)

    url = f"https://api.upbit.com/v1/candles/minutes/{fetch_minutes}?market={symbol}&count={fetch_count}"
    headers = {"accept": "application/json"}
    
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if not isinstance(res, list):
            return [], {}
    except Exception:
        return [], {}

    res.reverse()

    df = pd.DataFrame(res)
    df['candle_date_time_utc'] = pd.to_datetime(df['candle_date_time_utc'])
    df.set_index('candle_date_time_utc', inplace=True)

    if minutes not in upbit_native_minutes:
        rule = f"{minutes}T"
        resampled = df.resample(rule, closed='left', label='left').agg({
            'opening_price': 'first',
            'high_price': 'max',
            'low_price': 'min',
            'trade_price': 'last',
            'timestamp': 'last'
        }).dropna()
        df = resampled

    candles = []
    ma5, ma15, ma30, ma60, ma120 = [], [], [], [], []
    closes = []

    for idx, row in df.iterrows():
        time_sec = int(idx.timestamp())
        open_p = float(row["opening_price"])
        high_p = float(row["high_price"])
        low_p = float(row["low_price"])
        close_p = float(row["trade_price"])

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

upbit_candles, upbit_mas = get_upbit_klines(symbol_upbit, target_minutes)

st.subheader(f"🇰🇷 업비트 ({symbol_upbit}) - {current_tf}")
if upbit_candles:
    renderLightweightCharts([build_chart_config(upbit_candles, upbit_mas)], key=f"upbit_chart_{current_tf}")

# ---------------------------------------------------------
# 2. 하단: 바이낸스 실시간 차트
# ---------------------------------------------------------
st.subheader(f"🌐 바이낸스 선물 실시간 ({symbol_binance_tv.split(':')[1]}) - {current_tf}")

tv_interval = tv_intervals.get(target_minutes, "15")

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
