import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit_lightweight_charts import renderLightweightCharts

# 웹 페이지 기본 설정
st.set_page_config(
    page_title="Crypto Smart Signal Dashboard", page_icon="🚀", layout="wide"
)

# ---------------------------------------------------------
# 0. 실시간 자동 새로고침 (5초 간격)
# ---------------------------------------------------------
st.components.v1.html(
    """
    <script>
        setTimeout(function(){
            window.parent.postMessage({type: 'streamlit:render'}, '*');
        }, 5000);
    </script>
    """,
    height=0,
)

# ---------------------------------------------------------
# 1. 코인 목록 설정
# ---------------------------------------------------------
COIN_MAP = {
    "XRP (리플)": {"upbit": "KRW-XRP", "binance": "BINANCE:XRPUSDT.P"},
    "ZEC (제트캐시)": {"upbit": "KRW-ZEC", "binance": "BINANCE:ZECUSDT.P"},
    "BTC (비트코인)": {"upbit": "KRW-BTC", "binance": "BINANCE:BTCUSDT.P"},
    "ETH (이더리움)": {"upbit": "KRW-ETH", "binance": "BINANCE:ETHUSDT.P"},
    "SOL (솔라나)": {"upbit": "KRW-SOL", "binance": "BINANCE:SOLUSDT.P"},
    "DOGE (도지코인)": {"upbit": "KRW-DOGE", "binance": "BINANCE:DOGEUSDT.P"},
}

st.sidebar.header("🔍 코인 선택")
selected_coin_name = st.sidebar.selectbox(
    "코인을 선택하세요",
    options=list(COIN_MAP.keys()),
    index=0
)

symbol_upbit = COIN_MAP[selected_coin_name]["upbit"]
symbol_binance_tv = COIN_MAP[selected_coin_name]["binance"]
binance_ticker = symbol_binance_tv.split(":")[1].replace(".P", "")

if "tf_choice" not in st.session_state:
    st.session_state["tf_choice"] = "1시간"

timeframe_to_minutes = {"1분": 1, "3분": 3, "5분": 5, "15분": 15, "1시간": 60, "4시간": 240}
tv_intervals = {1: "1", 3: "3", 5: "5", 15: "15", 60: "60", 240: "240"}

# ---------------------------------------------------------
# 상단 헤더 & 타임프레임 선택
# ---------------------------------------------------------
st.title(f"📊 {selected_coin_name} 스마트 히스토리 시그널 차트")

quick_tfs = ["1분", "3분", "5분", "15분", "1시간"]

def on_btn_click(selected):
    st.session_state["tf_choice"] = selected

c1, c2, c3, c4, c5 = st.columns(5)
for idx, q_tf in enumerate(quick_tfs):
    is_selected = (st.session_state["tf_choice"] == q_tf)
    [c1, c2, c3, c4, c5][idx].button(
        q_tf,
        key=f"btn_{q_tf}",
        use_container_width=True,
        on_click=on_btn_click,
        args=(q_tf,),
        type="primary" if is_selected else "secondary"
    )

current_tf = st.session_state["tf_choice"]
target_minutes = timeframe_to_minutes[current_tf]

# ---------------------------------------------------------
# 2. 과거 데이터 전체 스캔 및 롱/숏 누적 표기 알고리즘
# ---------------------------------------------------------
def get_upbit_data_and_signals(symbol, minutes):
    # 과거 데이터 스캔 개수를 500개로 확대
    url = f"https://api.upbit.com/v1/candles/minutes/{minutes}?market={symbol}&count=500"
    try:
        res = requests.get(url, headers={"accept": "application/json"}, timeout=5).json()
        if not isinstance(res, list) or len(res) == 0:
            return [], {}, [], "NEUTRAL"
    except Exception:
        return [], {}, [], "NEUTRAL"

    res.reverse()
    df = pd.DataFrame(res)
    df['candle_date_time_utc'] = pd.to_datetime(df['candle_date_time_utc'])
    df.set_index('candle_date_time_utc', inplace=True)

    # 주요 보조지표 산출
    df['ma5'] = df['trade_price'].rolling(5).mean()
    df['ma15'] = df['trade_price'].rolling(15).mean()
    df['goya_line'] = df['trade_price'].rolling(50).mean() # GOYA LINE
    df['smart_line'] = df['trade_price'].rolling(120).mean() # Smart Line
    df['vol_ma20'] = df['candle_acc_trade_volume'].rolling(20).mean()

    candles = []
    ma5_data, ma15_data, goya_data, smart_data = [], [], [], []
    markers = []
    latest_signal = "NEUTRAL"
    last_signal_type = None # 연속 중복 시그널 방지용

    for i in range(len(df)):
        row = df.iloc[i]
        time_sec = int(row['timestamp'] / 1000)
        close_p = float(row['trade_price'])
        open_p = float(row['opening_price'])
        high_p = float(row['high_price'])
        low_p = float(row['low_price'])
        vol = float(row['candle_acc_trade_volume'])
        vol_ma = float(row['vol_ma20']) if pd.notnull(row['vol_ma20']) else 0

        candles.append({"time": time_sec, "open": open_p, "high": high_p, "low": low_p, "close": close_p})

        if pd.notnull(row['ma5']): ma5_data.append({"time": time_sec, "value": float(row['ma5'])})
        if pd.notnull(row['ma15']): ma15_data.append({"time": time_sec, "value": float(row['ma15'])})
        if pd.notnull(row['goya_line']): goya_data.append({"time": time_sec, "value": float(row['goya_line'])})
        if pd.notnull(row['smart_line']): smart_data.append({"time": time_sec, "value": float(row['smart_line'])})

        # 과거 전체 구간 시그널 감지 조건
        if i >= 50 and pd.notnull(row['goya_line']):
            goya = row['goya_line']
            ma5 = row['ma5']
            ma15 = row['ma15']
            
            # 거래량 충족 여부 (평균 대비 1.3배 이상)
            is_volume_ok = (vol >= vol_ma * 1.3) if vol_ma > 0 else True

            # LONG 조건: 거래량이 실리면서 GOYA LINE 상단 유지 + 단기 골든크로스 상태
            if is_volume_ok and close_p > goya and ma5 > ma15:
                if last_signal_type != "LONG": # 추세 변경 시점에 표시
                    markers.append({
                        "time": time_sec,
                        "position": "belowBar",
                        "color": "#00E676",
                        "shape": "arrowUp",
                        "text": "L (LONG)"
                    })
                    last_signal_type = "LONG"
                    latest_signal = "LONG"

            # SHORT 조건: 거래량이 실리면서 GOYA LINE 하단 유지 + 단기 데드크로스 상태
            elif is_volume_ok and close_p < goya and ma5 < ma15:
                if last_signal_type != "SHORT": # 추세 변경 시점에 표시
                    markers.append({
                        "time": time_sec,
                        "position": "aboveBar",
                        "color": "#FF5252",
                        "shape": "arrowDown",
                        "text": "S (SHORT)"
                    })
                    last_signal_type = "SHORT"
                    latest_signal = "SHORT"

    mas = {"ma5": ma5_data, "ma15": ma15_data, "goya": goya_data, "smart": smart_data}
    return candles, mas, markers, latest_signal

upbit_candles, upbit_mas, markers, latest_signal = get_upbit_data_and_signals(symbol_upbit, target_minutes)

# 대시보드상 상태판
col_sig, col_count = st.columns([1, 2])
with col_sig:
    if latest_signal == "LONG":
        st.success("🟢 **현재 상태: LONG (매수 유입)**")
    elif latest_signal == "SHORT":
        st.error("🔴 **현재 상태: SHORT (매도 유입)**")
    else:
        st.info("⚪ **현재 상태: 관망 (NEUTRAL)**")

with col_count:
    st.write(f"📌 **과거 포착된 스마트 시그널 총 개수:** `{len(markers)}개` (차트를 좌우로 드래그하여 확인하세요)")

# Lightweight Charts 구성
def build_chart_config(candles, ma_dict, markers):
    chart_options = {
        "height": 500,
        "layout": {"background": {"type": "solid", "color": "#131722"}, "textColor": "#d1d4dc"},
        "grid": {"vertLines": {"color": "#1f2937"}, "horzLines": {"color": "#1f2937"}},
        "timeScale": {"timeVisible": True, "secondsVisible": False}
    }

    series = [
        {"type": "Candlestick", "data": candles, "markers": markers, "options": {"upColor": "#26a69a", "downColor": "#ef5350"}},
        {"type": "Line", "data": ma_dict["ma5"], "options": {"color": "#00e676", "lineWidth": 1, "title": "5선"}},
        {"type": "Line", "data": ma_dict["ma15"], "options": {"color": "#29b6f6", "lineWidth": 1, "title": "15선"}},
        {"type": "Line", "data": ma_dict["goya"], "options": {"color": "#e91e63", "lineWidth": 3, "title": "GOYA LINE"}},
        {"type": "Line", "data": ma_dict["smart"], "options": {"color": "#ffeb3b", "lineWidth": 2, "title": "Smart Line"}}
    ]

    return {"chart": chart_options, "series": series}

if upbit_candles:
    renderLightweightCharts([build_chart_config(upbit_candles, upbit_mas, markers)], key=f"chart_{symbol_upbit}_{current_tf}")

# 바이낸스 선물 차트 연동
st.subheader(f"🌐 바이낸스 선물 실시간 ({binance_ticker})")
tv_interval = tv_intervals.get(target_minutes, "60")
tradingview_html = f"""
<div class="tradingview-widget-container" style="height:480px;width:100%;">
  <div id="tradingview_binance" style="height:480px;width:100%;"></div>
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
    "container_id": "tradingview_binance"
  }});
  </script>
</div>
"""
components.html(tradingview_html, height=485)
