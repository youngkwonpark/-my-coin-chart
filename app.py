import datetime
import pandas as pd
import requests
import streamlit as st
from streamlit_lightweight_charts import renderLightweightCharts

# ---------------------------------------------------------
# 0. 스타일 설정 (노안 맞춤형 초대형 폰트 및 가독성 최적화)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Goya Chart App", page_icon="📈", layout="centered"
)

st.markdown(
    """
    <style>
    .stApp { background-color: #121212; color: #FFFFFF; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
    .block-container { padding: 0px !important; max-width: 100% !important; }
    
    /* 상단 헤더 */
    .goya-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: #1e1e1e;
        padding: 16px 20px;
        border-bottom: 1px solid #333333;
    }
    .goya-title {
        font-size: 26px;
        font-weight: bold;
        color: #ffffff;
        text-align: center;
        flex-grow: 1;
    }
    .goya-back {
        font-size: 28px;
        color: #ffffff;
        cursor: pointer;
        text-decoration: none;
    }
    .goya-subbar {
        background-color: #181818;
        padding: 16px 20px;
        border-bottom: 1px solid #2c2c2c;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    div[data-baseweb="select"] > div {
        font-size: 20px !important;
        font-weight: bold !important;
        background-color: #262626 !important;
        color: #ffffff !important;
        border: 1px solid #444444 !important;
    }
    .stButton > button {
        font-size: 16px !important;
        font-weight: bold !important;
        padding: 10px 0px !important;
        background-color: #262626 !important;
        color: #ffffff !important;
        border: 1px solid #444444 !important;
    }
    .goya-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: #1a1a1a;
        border-top: 1px solid #2c2c2c;
        display: flex;
        justify-content: space-around;
        padding: 12px 0;
        z-index: 999;
    }
    .goya-nav-item {
        text-align: center;
        color: #888888;
        font-size: 16px;
    }
    .goya-nav-item.active {
        color: #ff9800;
        font-weight: bold;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 1. 세션 상태 초기화 (안전 기본값 설정)
# ---------------------------------------------------------
if "selected_coin" not in st.session_state:
    st.session_state.selected_coin = "XRP/USDT"
if "show_candle" not in st.session_state:
    st.session_state.show_candle = True
if "show_goya" not in st.session_state:
    st.session_state.show_goya = True
if "show_smart" not in st.session_state:
    st.session_state.show_smart = True
if "show_tf_box" not in st.session_state:
    st.session_state.show_tf_box = False
if (
    "tf_choice" not in st.session_state
    or st.session_state.tf_choice not in ["1분", "3분", "5분", "15분", "30분", "45분", "1시간", "2시간", "4시간", "6시간", "8시간", "12시간"]
):
    st.session_state.tf_choice = "1시간"

SYMBOL_MAP = {
    "XRP/USDT": "KRW-XRP",
    "SOL/USDT": "KRW-SOL",
    "BTC/USDT": "KRW-BTC",
    "ETH/USDT": "KRW-ETH",
    "DOGE/USDT": "KRW-DOGE",
    "ADA/USDT": "KRW-ADA",
}

# 타임프레임 정의 (오류 방지를 위해 표준 명칭 사용)
TF_CONFIG = {
    "1분": {"path": "minutes/1"},
    "3분": {"path": "minutes/3"},
    "5분": {"path": "minutes/5"},
    "15분": {"path": "minutes/15"},
    "30분": {"path": "minutes/30"},
    "45분": {"path": "minutes/45"},
    "1시간": {"path": "minutes/60"},
    "2시간": {"path": "minutes/120"},
    "4시간": {"path": "minutes/240"},
    "6시간": {"path": "minutes/360"},
    "8시간": {"path": "minutes/480"},
    "12시간": {"path": "minutes/720"},
}

# ---------------------------------------------------------
# 2. 상단 헤더 및 좌우 코인 선택 & 검색 바
# ---------------------------------------------------------
st.markdown(
    f"""
    <div class="goya-header">
        <a class="goya-back" href="#">＜</a>
        <div class="goya-title">{st.session_state.selected_coin}</div>
        <div style="width: 25px;"></div>
    </div>
""",
    unsafe_allow_html=True,
)

with st.container():
    st.markdown(
        '<div style="background-color: #181818; padding: 14px 16px; border-bottom: 2px solid #333;">',
        unsafe_allow_html=True,
    )

    col_select, col_search = st.columns([1, 2.5])

    with col_select:
        available_coins = list(SYMBOL_MAP.keys())
        selected_coin = st.selectbox(
            "코인 선택",
            available_coins,
            index=available_coins.index(st.session_state.selected_coin),
            key="coin_selectbox_widget",
            label_visibility="collapsed",
        )
        if selected_coin != st.session_state.selected_coin:
            st.session_state.selected_coin = selected_coin
            st.rerun()

    with col_search:
        coin_search_input = st.text_input(
            "🔍 코인명 직접 검색 (예: XRP)",
            placeholder="🔍 돋보기 코인 검색 (예: XRP, BTC)",
            label_visibility="collapsed",
        )
        if coin_search_input:
            matched = [
                c
                for c in available_coins
                if coin_search_input.upper() in c.upper()
            ]
            if matched and matched[0] != st.session_state.selected_coin:
                st.session_state.selected_coin = matched[0]
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

market_code = SYMBOL_MAP[st.session_state.selected_coin]


# ---------------------------------------------------------
# 3. 우측 화살표로 여닫는 타임프레임 선택 바
# ---------------------------------------------------------
st.markdown(
    '<div style="background-color: #141414; padding: 12px 16px; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center;">',
    unsafe_allow_html=True,
)
st.markdown(
    f"<span style='color: #ff9800; font-weight: bold; font-size: 18px;'>선택된 봉: {st.session_state.tf_choice}</span>",
    unsafe_allow_html=True,
)

toggle_btn_label = (
    "타임프레임 닫기 ▲" if st.session_state.show_tf_box else "타임프레임 선택 ▼"
)
if st.button(toggle_btn_label, key="tf_toggle_btn"):
    st.session_state.show_tf_box = not st.session_state.show_tf_box
    st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.show_tf_box:
    st.markdown(
        '<div style="background-color: #1a1a1a; padding: 12px; border-bottom: 1px solid #333;">',
        unsafe_allow_html=True,
    )
    tf_keys = list(TF_CONFIG.keys())
    for i in range(0, len(tf_keys), 4):
        row_keys = tf_keys[i : i + 4]
        cols = st.columns(len(row_keys))
        for idx, tf_name in enumerate(row_keys):
            with cols[idx]:
                is_selected = st.session_state.tf_choice == tf_name
                if st.button(
                    tf_name,
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                    key=f"tf_popup_{tf_name}",
                ):
                    st.session_state.tf_choice = tf_name
                    st.session_state.show_tf_box = False
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

tf_path = TF_CONFIG[st.session_state.tf_choice]["path"]


# ---------------------------------------------------------
# 4. [요청 반영] 지표 설정 문구 없이 3가지 지표 박스 항시 노출
# ---------------------------------------------------------
st.markdown(
    '<div style="background-color: #181818; padding: 12px 16px; border-bottom: 2px solid #333;">',
    unsafe_allow_html=True,
)
mc1, mc2, mc3 = st.columns(3)
with mc1:
    st.session_state.show_candle = st.checkbox(
        "캔들", value=st.session_state.show_candle
    )
with mc2:
    st.session_state.show_goya = st.checkbox(
        "GOYA", value=st.session_state.show_goya
    )
with mc3:
    st.session_state.show_smart = st.checkbox(
        "Smart", value=st.session_state.show_smart
    )
st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# 5. 데이터 수집 및 KST 시간 보정 로직
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
                            "text": "LONG",
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
                            "text": "SHORT",
                        }
                    )
                    last_sig = "SHORT"

        return (
            candles,
            {"goya": goya_data, "smart": smart_data},
            markers,
            df,
        )
    except Exception:
        return None, None, None, None


data_package = get_chart_data(market_code, tf_path)

if data_package[0] is None:
    st.error("⚠️ 데이터를 불러오는 중입니다. 잠시 후 새로고침해 주세요.")
else:
    candles, mas, markers, df_full = data_package
    latest_info = df_full.iloc[-1]

    pct_val = (
        latest_info["change_pct"]
        if pd.notnull(latest_info["change_pct"])
        else 0.0
    )
    pct_color = "#26a69a" if pct_val >= 0 else "#ef5350"
    pct_str = f"+{pct_val:.2f}%" if pct_val >= 0 else f"{pct_val:.2f}%"

    # 상단 가격 정보 박스
    st.markdown(
        f"""
        <div class="goya-subbar">
            <span style="font-size: 30px; font-weight: bold; color: #ffffff;">{latest_info['close']:,.1f}</span>
            <span style="font-size: 22px; font-weight: bold; color: {pct_color};">{pct_str}</span>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # 차트 바로 위 정보 박스
    st.markdown(
        f"""
        <div style="
            background: #141414;
            border-bottom: 1px solid #2c2c2c;
            padding: 14px 20px;
            font-size: 18px;
            color: #d1d4dc;
            line-height: 1.7;
        ">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="color: #ff9800; font-weight: bold; font-size: 22px;">{st.session_state.selected_coin} ({st.session_state.tf_choice})</span>
                <span style="color: #8bc34a; font-weight: bold; font-size: 18px;">{latest_info['dt_str']}</span>
            </div>
            시가 <span style="color:#fff; font-weight: bold; font-size: 19px;">{latest_info['open']:,.1f}</span> &nbsp;|&nbsp; 
            고가 <span style="color:#26a69a; font-weight: bold; font-size: 19px;">{latest_info['high']:,.1f}</span><br>
            저가 <span style="color:#ef5350; font-weight: bold; font-size: 19px;">{latest_info['low']:,.1f}</span> &nbsp;|&nbsp; 
            종가 <span style="color:#2196f3; font-weight: bold; font-size: 19px;">{latest_info['close']:,.1f}</span><br>
            <span style="color: #e91e63; font-weight: bold; font-size: 20px;">GOYA: {latest_info['goya_line']:,.1f}</span> &nbsp;&nbsp;
            <span style="color: #ffeb3b; font-weight: bold; font-size: 20px;">Smart: {latest_info['smart_line']:,.1f}</span>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------------
    # 6. 트레이딩뷰 차트 렌더링
    # ---------------------------------------------------------
    chart_options = {
        "height": 580,
        "layout": {
            "background": {"color": "#121212"},
            "textColor": "#ffffff",
            "fontSize": 16,
        },
        "grid": {
            "vertLines": {"color": "#1f1f1f"},
            "horzLines": {"color": "#1f1f1f"},
        },
        "timeScale": {
            "timeVisible": True,
            "secondsVisible": False,
            "rightOffset": 12,
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
                    "lineWidth": 3,
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
                    "lineWidth": 3,
                    "title": "Smart Line",
                },
            }
        )

    renderLightweightCharts(
        [{"chart": chart_options, "series": series}],
        key=f"goya_chart_{market_code}_{tf_path}",
    )

# ---------------------------------------------------------
# 7. 하단 네비게이션바
# ---------------------------------------------------------
st.markdown(
    """
    <div style="height: 60px;"></div>
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
