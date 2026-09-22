import datetime
import pandas as pd
import requests
import streamlit as st
from streamlit_lightweight_charts import renderLightweightCharts

# ---------------------------------------------------------
# 0. 기본 설정 및 모바일 최적화 레이아웃
# ---------------------------------------------------------
st.set_page_config(
    page_title="Goya Signal Precision Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #111318; color: #FFFFFF; }
    .block-container { padding-top: 0.5rem; padding-bottom: 0.5rem; padding-left: 0.5rem; padding-right: 0.5rem; max-width: 100%; }
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 1. 상단 네비게이션: 코인 선택 및 타임프레임 컨트롤
# ---------------------------------------------------------
SYMBOL_MAP = {
    "XRP (리플)": "KRW-XRP",
    "SOL (솔라나)": "KRW-SOL",
    "BTC (비트코인)": "KRW-BTC",
    "ETH (이더리움)": "KRW-ETH",
}

col_coin, col_tf1, col_tf2, col_tf3, col_tf4, col_tf5, col_tf6 = st.columns(
    [2, 1, 1, 1, 1, 1, 1]
)

with col_coin:
    selected_coin = st.selectbox(
        "코인 선택", list(SYMBOL_MAP.keys()), label_visibility="collapsed"
    )

market_code = SYMBOL_MAP[selected_coin]

if "tf_choice" not in st.session_state:
    st.session_state.tf_choice = "1시간"

with col_tf1:
    if st.button("1분", use_container_width=True):
        st.session_state.tf_choice = "1분"
with col_tf2:
    if st.button("3분", use_container_width=True):
        st.session_state.tf_choice = "3분"
with col_tf3:
    if st.button("5분", use_container_width=True):
        st.session_state.tf_choice = "5분"
with col_tf4:
    if st.button("15분", use_container_width=True):
        st.session_state.tf_choice = "15분"
with col_tf5:
    if st.button("1시간", use_container_width=True):
        st.session_state.tf_choice = "1시간"
with col_tf6:
    if st.button("4시간", use_container_width=True):
        st.session_state.tf_choice = "4시간"

current_tf_label = st.session_state.tf_choice

timeframe_map = {
    "1분": "minutes/1",
    "3분": "minutes/3",
    "5분": "minutes/5",
    "15분": "minutes/15",
    "1시간": "minutes/60",
    "4시간": "minutes/240",
}
tf_path = timeframe_map[current_tf_label]


# ---------------------------------------------------------
# 2. 데이터 수집 및 KST 시간 왜곡 해결 가공
# ---------------------------------------------------------
@st.cache_data(ttl=5)
def get_chart_data(market, tf):
    url = f"https://api.upbit.com/v1/candles/{tf}?market={market}&count=200"
    headers = {"accept": "application/json"}

    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if not isinstance(res, list) or len(res) == 0:
            return None, None, None, None

        res.reverse()
        df = pd.DataFrame(res)

        # KST 타임스탬프 완벽 고정 (UTC 밀림 현상 방지)
        dt_kst = pd.to_datetime(df["candle_date_time_kst"])
        df["time"] = dt_kst.apply(
            lambda x: int(
                x.replace(
                    tzinfo=datetime.timezone(datetime.timedelta(hours=9))
                ).timestamp()
            )
        )
        df["dt_str"] = dt_kst.dt.strftime("%Y-%m-%d %H:%M")

        df["open"] = df["opening_price"]
        df["high"] = df["high_price"]
        df["low"] = df["low_price"]
        df["close"] = df["trade_price"]

        # 등락률 계산
        df["change_pct"] = df["close"].pct_change() * 100

        # 이동평균선 (고야라인 20선, 스마트라인 50선)
        df["goya_line"] = df["close"].rolling(20).mean()
        df["smart_line"] = df["close"].rolling(50).mean()

        candles = []
        goya_data, smart_data = [], []
        markers = []
        last_sig = None

        for i in range(len(df)):
            row = df.iloc[i]
            t_sec = int(row["time"])

            c_p = float(row["close"])
            o_p = float(row["open"])
            h_p = float(row["high"])
            l_p = float(row["low"])

            candles.append(
                {
                    "time": t_sec,
                    "open": o_p,
                    "high": h_p,
                    "low": l_p,
                    "close": c_p,
                }
            )

            if pd.notnull(row["goya_line"]):
                goya_data.append(
                    {"time": t_sec, "value": float(row["goya_line"])}
                )
            if pd.notnull(row["smart_line"]):
                smart_data.append(
                    {"time": t_sec, "value": float(row["smart_line"])}
                )

            # 시그널 판정
            if (
                i >= 50
                and pd.notnull(row["goya_line"])
                and pd.notnull(row["smart_line"])
            ):
                goya = row["goya_line"]
                smart = row["smart_line"]

                if c_p > goya and c_p > smart and last_sig != "LONG":
                    markers.append(
                        {
                            "time": t_sec,
                            "position": "belowBar",
                            "color": "#00E676",
                            "shape": "arrowUp",
                            "text": "L",
                        }
                    )
                    last_sig = "LONG"
                elif c_p < goya and c_p < smart and last_sig != "SHORT":
                    markers.append(
                        {
                            "time": t_sec,
                            "position": "aboveBar",
                            "color": "#FF5252",
                            "shape": "arrowDown",
                            "text": "S",
                        }
                    )
                    last_sig = "SHORT"

        mas = {"goya": goya_data, "smart": smart_data}
        latest_info = df.iloc[-1]
        return candles, mas, markers, latest_info
    except Exception as e:
        return None, None, None, None


data_package = get_chart_data(market_code, tf_path)

if data_package[0] is None:
    st.error("⚠️ 데이터를 불러오는 중입니다. 잠시 후 새로고침해 주세요.")
else:
    candles, mas, markers, latest_info = data_package

    pct_val = (
        latest_info["change_pct"]
        if pd.notnull(latest_info["change_pct"])
        else 0.0
    )
    pct_color = "#26a69a" if pct_val >= 0 else "#ef5350"
    pct_str = f"+{pct_val:.2f}%" if pct_val >= 0 else f"{pct_val:.2f}%"

    # ---------------------------------------------------------
    # 3. 고야 차트 스타일: 좌측 상단 투명 오버레이 패널 (날짜, OHLCV, 변동률)[span_4](start_span)[span_4](end_span)
    # ---------------------------------------------------------
    st.markdown(
        f"""
        <div style="
            position: relative;
            z-index: 10;
            background: rgba(19, 23, 34, 0.85);
            border: 1px solid #2a2e39;
            padding: 8px 12px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            color: #d1d4dc;
            margin-bottom: -45px;
            width: fit-content;
            pointer-events: none;
        ">
            <span style="color: #ffeb3b; font-weight: bold;">{selected_coin.split(' ')[0]}</span> &nbsp;
            <span style="color: #9aca3c;">{latest_info['dt_str']}</span><br>
            O: <span style="color:#fff;">{latest_info['open']:,}</span> &nbsp;
            H: <span style="color:#26a69a;">{latest_info['high']:,}</span> &nbsp;
            L: <span style="color:#ef5350;">{latest_info['low']:,}</span> &nbsp;
            C: <span style="color:#2196f3;">{latest_info['close']:,}</span> &nbsp;
            <span style="color: {pct_color};">({pct_str})</span><br>
            <span style="color: #e91e63;">Goya: {latest_info['goya_line']:,.1f}</span> &nbsp;
            <span style="color: #ffeb3b;">Smart: {latest_info['smart_line']:,.1f}</span>
        </div>
    """,
        unsafe_allow_html=True,
    )

    chart_options = {
        "height": 550,
        "layout": {"background": {"color": "#131722"}, "textColor": "#d1d4dc"},
        "grid": {
            "vertLines": {"color": "#1f2937"},
            "horzLines": {"color": "#1f2937"},
        },
        "timeScale": {
            "timeVisible": True,
            "secondsVisible": False,
            "rightOffset": 12,
        },
    }

    series = [
        {
            "type": "Candlestick",
            "data": candles,
            "markers": markers,
            "options": {"upColor": "#26a69a", "downColor": "#ef5350"},
        },
        {
            "type": "Line",
            "data": mas["goya"],
            "options": {
                "color": "#e91e63",
                "lineWidth": 3,
                "title": "GOYA LINE",
            },
        },
        {
            "type": "Line",
            "data": mas["smart"],
            "options": {
                "color": "#ffeb3b",
                "lineWidth": 2,
                "title": "Smart Line",
            },
        },
    ]

    renderLightweightCharts(
        [{"chart": chart_options, "series": series}],
        key=f"chart_{market_code}_{tf_path}",
    )
