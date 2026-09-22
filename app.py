import datetime
import pandas as pd
import requests
import streamlit as st
from streamlit_lightweight_charts import renderLightweightCharts

# ---------------------------------------------------------
# 0. 기본 설정 (고야 앱 모바일 스타일 레이아웃)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Goya Chart App", page_icon="📈", layout="centered"
)

st.markdown(
    """
    <style>
    .stApp { background-color: #121212; color: #FFFFFF; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
    .block-container { padding: 0px !important; max-width: 100% !important; }
    
    /* 고야 앱 스타일 상단 헤더 */
    .goya-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: #1e1e1e;
        padding: 12px 16px;
        border-bottom: 1px solid #2c2c2c;
    }
    .goya-title {
        font-size: 18px;
        font-weight: bold;
        color: #ffffff;
        text-align: center;
        flex-grow: 1;
    }
    .goya-back {
        font-size: 20px;
        color: #ffffff;
        cursor: pointer;
        text-decoration: none;
    }
    .goya-subbar {
        background-color: #181818;
        padding: 10px 16px;
        border-bottom: 1px solid #2c2c2c;
    }
    /* 하단 앱 네비게이션바 스타일 */
    .goya-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: #1a1a1a;
        border-top: 1px solid #2c2c2c;
        display: flex;
        justify-content: space-around;
        padding: 8px 0;
        z-index: 999;
    }
    .goya-nav-item {
        text-align: center;
        color: #888888;
        font-size: 11px;
    }
    .goya-nav-item.active {
        color: #ff9800;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 1. 세션 상태 초기화
# ---------------------------------------------------------
if "selected_coin" not in st.session_state:
    st.session_state.selected_coin = "XRP/USDT"
if "show_candle" not in st.session_state:
    st.session_state.show_candle = True
if "show_goya" not in st.session_state:
    st.session_state.show_goya = True
if "show_smart" not in st.session_state:
    st.session_state.show_smart = True
if "show_sr" not in st.session_state:
    st.session_state.show_sr = False
if "show_trend" not in st.session_state:
    st.session_state.show_trend = False
if "show_trend1" not in st.session_state:
    st.session_state.show_trend1 = False
if "show_menu" not in st.session_state:
    st.session_state.show_menu = False
if "tf_choice" not in st.session_state:
    st.session_state.tf_choice = "1시간"

SYMBOL_MAP = {
    "XRP/USDT": "KRW-XRP",
    "SOL/USDT": "KRW-SOL",
    "BTC/USDT": "KRW-BTC",
    "ETH/USDT": "KRW-ETH",
}

# ---------------------------------------------------------
# 2. 상단 네비게이션바 및 코인/타임프레임 컨트롤
# ---------------------------------------------------------
st.markdown(
    f"""
    <div class="goya-header">
        <a class="goya-back" href="#">＜</a>
        <div class="goya-title">{st.session_state.selected_coin}</div>
        <div style="width: 20px;"></div>
    </div>
""",
    unsafe_allow_html=True,
)

col_c1, col_tf1, col_tf2, col_tf3, col_tf4 = st.columns([1.6, 1, 1, 1, 1])

with col_c1:
    selected_coin = st.selectbox(
        "코인 선택",
        list(SYMBOL_MAP.keys()),
        index=list(SYMBOL_MAP.keys()).index(st.session_state.selected_coin),
        key="coin_selectbox_widget",
        label_visibility="collapsed",
    )
    if selected_coin != st.session_state.selected_coin:
        st.session_state.selected_coin = selected_coin
        st.rerun()

market_code = SYMBOL_MAP[st.session_state.selected_coin]

with col_tf1:
    if st.button(
        "1분",
        use_container_width=True,
        type="primary"
        if st.session_state.tf_choice == "1분"
        else "secondary",
    ):
        st.session_state.tf_choice = "1분"
        st.rerun()
with col_tf2:
    if st.button(
        "5분",
        use_container_width=True,
        type="primary"
        if st.session_state.tf_choice == "5분"
        else "secondary",
    ):
        st.session_state.tf_choice = "5분"
        st.rerun()
with col_tf3:
    if st.button(
        "1시간",
        use_container_width=True,
        type="primary"
        if st.session_state.tf_choice == "1시간"
        else "secondary",
    ):
        st.session_state.tf_choice = "1시간"
        st.rerun()
with col_tf4:
    if st.button(
        "4시간",
        use_container_width=True,
        type="primary"
        if st.session_state.tf_choice == "4시간"
        else "secondary",
    ):
        st.session_state.tf_choice = "4시간"
        st.rerun()

timeframe_map = {
    "1분": "minutes/1",
    "5분": "minutes/5",
    "1시간": "minutes/60",
    "4시간": "minutes/240",
}
tf_path = timeframe_map[st.session_state.tf_choice]


# ---------------------------------------------------------
# 3. 스마트 차트 설정 드롭다운 메뉴
# ---------------------------------------------------------
col_menu_btn, _ = st.columns([2, 5])
with col_menu_btn:
    if st.button(
        "⚙️ 스마트 차트 설정 ▾", use_container_width=True, type="tertiary"
    ):
        st.session_state.show_menu = not st.session_state.show_menu
        st.rerun()

if st.session_state.show_menu:
    with st.container():
        st.markdown(
            """
            <div style="background-color: #1e1e1e; padding: 12px; border: 1px solid #333; border-radius: 8px; margin-bottom: 10px;">
                <div style="font-weight: bold; color: #ff9800; margin-bottom: 8px; font-size: 13px;">지표 필터 설정</div>
            </div>
        """,
            unsafe_allow_html=True,
        )
        mc1, mc2 = st.columns(2)
        with mc1:
            st.session_state.show_candle = st.checkbox(
                "Candle", value=st.session_state.show_candle
            )
            st.session_state.show_trend1 = st.checkbox(
                "Trend 1", value=st.session_state.show_trend1
            )
            st.session_state.show_goya = st.checkbox(
                "GOYA LINE", value=st.session_state.show_goya
            )
        with mc2:
            st.session_state.show_trend = st.checkbox(
                "Trend", value=st.session_state.show_trend
            )
            st.session_state.show_smart = st.checkbox(
                "Smart Line", value=st.session_state.show_smart
            )
            st.session_state.show_sr = st.checkbox(
                "S/R", value=st.session_state.show_sr
            )


# ---------------------------------------------------------
# 4. 데이터 수집 및 오차 개선된 시그널 조건 로직
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
        df["change_pct"] = df["close"].pct_change() * 100

        df["goya_line"] = df["close"].rolling(20).mean()
        df["smart_line"] = df["close"].rolling(50).mean()

        candles = []
        goya_data, smart_data = [], []
        markers = []
        last_sig = None

        for i in range(len(df)):
            row = df.iloc[i]
            t_sec = int(row["time"])
            c_p, o_p, h_p, l_p = (
                float(row["close"]),
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
            )

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

            if (
                i >= 50
                and pd.notnull(row["goya_line"])
                and pd.notnull(row["smart_line"])
            ):
                goya, smart = row["goya_line"], row["smart_line"]
                if (
                    c_p > goya
                    and c_p > smart
                    and goya >= smart
                    and last_sig != "LONG"
                ):
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
                elif (
                    c_p < goya
                    and c_p < smart
                    and goya <= smart
                    and last_sig != "SHORT"
                ):
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

        return (
            candles,
            {"goya": goya_data, "smart": smart_data},
            markers,
            df.iloc[-1],
        )
    except Exception:
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

    st.markdown(
        f"""
        <div class="goya-subbar">
            <span style="font-size: 20px; font-weight: bold; color: #ffffff;">{latest_info['close']:,.1f}</span>
            <span style="font-size: 14px; font-weight: bold; color: {pct_color}; margin-left: 10px;">{pct_str}</span>
        </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style="
            background: #141414;
            border-bottom: 1px solid #2c2c2c;
            padding: 8px 16px;
            font-family: monospace;
            font-size: 12px;
            color: #d1d4dc;
        ">
            <span style="color: #ff9800; font-weight: bold;">{st.session_state.selected_coin}</span> &nbsp;
            <span style="color: #8bc34a;">{latest_info['dt_str']}</span><br>
            O: <span style="color:#fff;">{latest_info['open']:,.1f}</span> &nbsp;
            H: <span style="color:#26a69a;">{latest_info['high']:,.1f}</span> &nbsp;
            L: <span style="color:#ef5350;">{latest_info['low']:,.1f}</span> &nbsp;
            C: <span style="color:#2196f3;">{latest_info['close']:,.1f}</span><br>
            <span style="color: #e91e63;">Goya: {latest_info['goya_line']:,.1f}</span> &nbsp;
            <span style="color: #ffeb3b;">Smart: {latest_info['smart_line']:,.1f}</span>
        </div>
    """,
        unsafe_allow_html=True,
    )

    chart_options = {
        "height": 480,
        "layout": {"background": {"color": "#121212"}, "textColor": "#d1d4dc"},
        "grid": {
            "vertLines": {"color": "#1f1f1f"},
            "horzLines": {"color": "#1f1f1f"},
        },
        "timeScale": {
            "timeVisible": True,
            "secondsVisible": False,
            "rightOffset": 10,
        },
    }

    series = []
    if st.session_state.show_candle:
        series.append(
            {
                "type": "Candlestick",
                "data": candles,
                "markers": markers,
                "options": {"upColor": "#26a69a", "downColor": "#ef5350"},
            }
        )
    if st.session_state.show_goya:
        series.append(
            {
                "type": "Line",
                "data": mas["goya"],
                "options": {
                    "color": "#e91e63",
                    "lineWidth": 2,
                    "title": "GOYA LINE",
                },
            }
        )
    if st.session_state.show_smart:
        series.append(
            {
                "type": "Line",
                "data": mas["smart"],
                "options": {
                    "color": "#ffeb3b",
                    "lineWidth": 2,
                    "title": "Smart Line",
                },
            }
        )

    renderLightweightCharts(
        [{"chart": chart_options, "series": series}],
        key=f"goya_chart_{market_code}_{tf_path}",
    )

st.markdown(
    """
    <div class="goya-nav">
        <div class="goya-nav-item">🎛️ 마켓</div>
        <div class="goya-nav-item">💡 브리핑</div>
        <div class="goya-nav-item active">🏠 홈</div>
        <div class="goya-nav-item">🔔 알람</div>
        <div class="goya-nav-item">⚙️ 설정</div>
    </div>
""",
    unsafe_allow_html=True,
)
