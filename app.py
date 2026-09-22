import streamlit as st
import pandas as pd
import requests
import datetime
import streamlit.components.v1 as components
from streamlit_lightweight_charts import renderLightweightCharts

# ---------------------------------------------------------
# 0. 기본 설정 및 다크 테마
# ---------------------------------------------------------
st.set_page_config(page_title="Goya Signal Precision Dashboard", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #111318; color: #FFFFFF; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ GOYA SMART SIGNAL (KST 동기화)")

# ---------------------------------------------------------
# 1. 바이낸스 선물 실시간 API 수신 (시간대 KST 변환)
# ---------------------------------------------------------
SYMBOL_MAP = {
    "XRP (리플)": "XRPUSDT",
    "SOL (솔라나)": "SOLUSDT",
    "BTC (비트코인)": "BTCUSDT",
    "ETH (이더리움)": "ETHUSDT"
}

selected_coin = st.sidebar.selectbox("코인 선택", list(SYMBOL_MAP.keys()), index=0)
binance_symbol = SYMBOL_MAP[selected_coin]

timeframe_map = {
    "1분": "1m", "3분": "3m", "5분": "5m", 
    "15분": "15m", "1시간": "1h", "4시간": "4h"
}

tf_selected = st.sidebar.radio("타임프레임", list(timeframe_map.keys()), index=4) # 기본 1시간
interval = timeframe_map[tf_selected]

def get_binance_futures_kst(symbol, interval_str):
    # 바이낸스 선물 캔들 API 호출 (500개)
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval_str}&limit=500"
    try:
        res = requests.get(url, timeout=5).json()
        if not isinstance(res, list) or len(res) == 0:
            return [], {}, [], None
    except Exception:
        return [], {}, [], None

    df = pd.DataFrame(res, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'qav', 'num_trades', 'tb_base_av', 'tb_quote_av', 'ignore'
    ])

    # KST (한국시간, UTC+9) 오프셋 변환 (바이낸스 밀리초 타임스탬프 + 9시간)
    df['timestamp_kst_sec'] = (df['open_time'] / 1000) + (9 * 3600)
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)

    # 고야 지표 산출 (지수/단순 이동평균 튜닝)
    df['goya_line'] = df['close'].rolling(20).mean()   # GOYA LINE
    df['smart_line'] = df['close'].rolling(50).mean()  # Smart Line

    candles = []
    goya_data, smart_data = [], []
    markers = []
    last_sig = None

    for i in range(len(df)):
        row = df.iloc[i]
        t_sec = int(row['timestamp_kst_sec'])
        c_p = row['close']
        o_p = row['open']
        h_p = row['high']
        l_p = row['low']

        candles.append({"time": t_sec, "open": o_p, "high": h_p, "low": l_p, "close": c_p})

        if pd.notnull(row['goya_line']):
            goya_data.append({"time": t_sec, "value": float(row['goya_line'])})
        if pd.notnull(row['smart_line']):
            smart_data.append({"time": t_sec, "value": float(row['smart_line'])})

        # 고야 앱 시그널 골든/데드크로스 로직 동기화
        if i >= 50 and pd.notnull(row['goya_line']) and pd.notnull(row['smart_line']):
            goya = row['goya_line']
            smart = row['smart_line']
            prev_goya = df.iloc[i-1]['goya_line']
            prev_smart = df.iloc[i-1]['smart_line']

            # 롱 시그널: GOYA LINE이 Smart Line을 상향 돌파하거나 양봉 전환 시
            if (prev_goya <= prev_smart and goya > smart) or (c_p > goya and c_p > smart and last_sig != "LONG"):
                markers.append({
                    "time": t_sec,
                    "position": "belowBar",
                    "color": "#00E676",
                    "shape": "arrowUp",
                    "text": "L (LONG)"
                })
                last_sig = "LONG"

            # 숏 시그널: GOYA LINE이 Smart Line을 하향 이탈 시
            elif (prev_goya >= prev_smart and goya < smart) or (c_p < goya and c_p < smart and last_sig != "SHORT"):
                markers.append({
                    "time": t_sec,
                    "position": "aboveBar",
                    "color": "#FF5252",
                    "shape": "arrowDown",
                    "text": "S (SHORT)"
                })
                last_sig = "SHORT"

    mas = {"goya": goya_data, "smart": smart_data}
    latest_info = df.iloc[-1]
    return candles, mas, markers, latest_info

candles, mas, markers, latest_info = get_binance_futures_kst(binance_symbol, interval)

# ---------------------------------------------------------
# 2. OHLCV 정보 표시 패널
# ---------------------------------------------------------
if latest_info is not None:
    st.markdown("### 📌 실시간 OHLCV (한국 표준시 KST 기준)")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("시가 (Open)", f"{latest_info['open']:.4f}")
    c2.metric("고가 (High)", f"{latest_info['high']:.4f}")
    c3.metric("저가 (Low)", f"{latest_info['low']:.4f}")
    c4.metric("종가 (Close)", f"{latest_info['close']:.4f}")
    c5.metric("Goya Line", f"{latest_info['goya_line']:.4f}" if pd.notnull(latest_info['goya_line']) else "-")
    c6.metric("Smart Line", f"{latest_info['smart_line']:.4f}" if pd.notnull(latest_info['smart_line']) else "-")

# ---------------------------------------------------------
# 3. 차트 렌더링 (KST 타임스탬프 적용)
# ---------------------------------------------------------
def build_chart_config(candles, ma_dict, markers):
    chart_options = {
        "height": 550,
        "layout": {"background": {"type": "solid", "color": "#131722"}, "textColor": "#d1d4dc"},
        "grid": {"vertLines": {"color": "#1f2937"}, "horzLines": {"color": "#1f2937"}},
        "timeScale": {"timeVisible": True, "secondsVisible": False}
    }

    series = [
        {"type": "Candlestick", "data": candles, "markers": markers, "options": {"upColor": "#26a69a", "downColor": "#ef5350"}},
        {"type": "Line", "data": ma_dict["goya"], "options": {"color": "#e91e63", "lineWidth": 3, "title": "GOYA LINE"}},
        {"type": "Line", "data": ma_dict["smart"], "options": {"color": "#ffeb3b", "lineWidth": 2, "title": "Smart Line"}}
    ]

    return {"chart": chart_options, "series": series}

if candles:
    renderLightweightCharts([build_chart_config(candles, mas, markers)], key=f"chart_{binance_symbol}_{interval}")
