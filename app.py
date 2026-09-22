import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit_lightweight_charts import renderLightweightCharts

# ---------------------------------------------------------
# 0. 페이지 기본 설정 및 스타일
# ---------------------------------------------------------
st.set_page_config(
    page_title="Goya Smart Signal Dashboard", page_icon="📈", layout="wide"
)

# 다크 모드 스타일 적용
st.markdown(
    """
    <style>
    .stApp { background-color: #111318; color: #FFFFFF; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 1. 상단 카테고리 탭 (스마트 / 프리미엄 / NEXT / 신호등)
# ---------------------------------------------------------
st.title("🛡️ GOYA SIGNAL SYSTEM")

category_tabs = st.tabs(
    ["✨ 스마트 시그널", "💎 프리미엄 시그널", "🚀 NEXT 시그널", "🚦 신호등 시그널"]
)

# ---------------------------------------------------------
# 2. 스마트 시그널 카테고리 구현
# ---------------------------------------------------------
with category_tabs[0]:

    COIN_MAP = {
        "XRP (리플)": {"upbit": "KRW-XRP", "binance": "BINANCE:XRPUSDT.P"},
        "SOL (솔라나)": {"upbit": "KRW-SOL", "binance": "BINANCE:SOLUSDT.P"},
        "UNI (유니스왑)": {"upbit": "KRW-UNI", "binance": "BINANCE:UNIUSDT.P"},
        "BTC (비트코인)": {"upbit": "KRW-BTC", "binance": "BINANCE:BTCUSDT.P"},
        "ETH (이더리움)": {"upbit": "KRW-ETH", "binance": "BINANCE:ETHUSDT.P"},
    }

    col_coin, col_tf = st.columns([2, 3])

    with col_coin:
        selected_coin_name = st.selectbox(
            "코인 선택", options=list(COIN_MAP.keys()), index=0
        )

    symbol_upbit = COIN_MAP[selected_coin_name]["upbit"]
    symbol_binance_tv = COIN_MAP[selected_coin_name]["binance"]
    binance_ticker = symbol_binance_tv.split(":")[1].replace(".P", "")

    if "tf_choice" not in st.session_state:
        st.session_state["tf_choice"] = "1시간"

    timeframe_to_minutes = {
        "1분": 1,
        "3분": 3,
        "5분": 5,
        "15분": 15,
        "1시간": 60,
        "4시간": 240,
    }

    with col_tf:
        st.write("타임프레임")
        tf_cols = st.columns(5)
        quick_tfs = ["1분", "3분", "5분", "15분", "1시간"]

        def set_tf(tf):
            st.session_state["tf_choice"] = tf

        for idx, q_tf in enumerate(quick_tfs):
            is_active = st.session_state["tf_choice"] == q_tf
            tf_cols[idx].button(
                q_tf,
                key=f"btn_{q_tf}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
                on_click=set_tf,
                args=(q_tf,),
            )

    current_tf = st.session_state["tf_choice"]
    target_minutes = timeframe_to_minutes[current_tf]

    # ---------------------------------------------------------
    # 3. 고야(Goya) 기준 시그널 알고리즘 적용
    # ---------------------------------------------------------
    def get_goya_signals(symbol, minutes):
        url = f"https://api.upbit.com/v1/candles/minutes/{minutes}?market={symbol}&count=500"
        try:
            res = requests.get(
                url, headers={"accept": "application/json"}, timeout=5
            ).json()
            if not isinstance(res, list) or len(res) == 0:
                return [], {}, [], "NEUTRAL", None
        except Exception:
            return [], {}, [], "NEUTRAL", None

        res.reverse()
        df = pd.DataFrame(res)
        df["candle_date_time_kst"] = pd.to_datetime(df["candle_date_time_kst"])

        # 고야 지표 산출 (이동평균 기반)
        df["ma5"] = df["trade_price"].rolling(5).mean()
        df["ma15"] = df["trade_price"].rolling(15).mean()
        df["goya_line"] = df["trade_price"].rolling(20).mean()  # GOYA LINE
        df["smart_line"] = df["trade_price"].rolling(60).mean()  # Smart Line

        candles = []
        ma5_data, ma15_data, goya_data, smart_data = [], [], [], []
        markers = []
        latest_signal = "NEUTRAL"
        last_sig = None

        for i in range(len(df)):
            row = df.iloc[i]
            time_sec = int(row["timestamp"] / 1000)
            close_p = float(row["trade_price"])
            open_p = float(row["opening_price"])
            high_p = float(row["high_price"])
            low_p = float(row["low_price"])

            candles.append(
                {
                    "time": time_sec,
                    "open": open_p,
                    "high": high_p,
                    "low": low_p,
                    "close": close_p,
                }
            )

            if pd.notnull(row["ma5"]):
                ma5_data.append(
                    {"time": time_sec, "value": float(row["ma5"])}
                )
            if pd.notnull(row["ma15"]):
                ma15_data.append(
                    {"time": time_sec, "value": float(row["ma15"])}
                )
            if pd.notnull(row["goya_line"]):
                goya_data.append(
                    {"time": time_sec, "value": float(row["goya_line"])}
                )
            if pd.notnull(row["smart_line"]):
                smart_data.append(
                    {"time": time_sec, "value": float(row["smart_line"])}
                )

            # 시그널 판정 (스마트 라인 및 고야 라인 조건)
            if i >= 60 and pd.notnull(row["smart_line"]):
                goya = row["goya_line"]
                smart = row["smart_line"]

                # 롱 조건: 종가가 고야 라인과 스마트 라인을 모두 상향 돌파
                if close_p > goya and close_p > smart:
                    if last_sig != "LONG":
                        markers.append(
                            {
                                "time": time_sec,
                                "position": "belowBar",
                                "color": "#00E676",
                                "shape": "arrowUp",
                                "text": "L (LONG)",
                            }
                        )
                        last_sig = "LONG"
                        latest_signal = "LONG"

                # 숏 조건: 종가가 고야 라인 및 스마트 라인을 하향 이탈
                elif close_p < goya and close_p < smart:
                    if last_sig != "SHORT":
                        markers.append(
                            {
                                "time": time_sec,
                                "position": "aboveBar",
                                "color": "#FF5252",
                                "shape": "arrowDown",
                                "text": "S (SHORT)",
                            }
                        )
                        last_sig = "SHORT"
                        latest_signal = "SHORT"

        mas = {
            "ma5": ma5_data,
            "ma15": ma15_data,
            "goya": goya_data,
            "smart": smart_data,
        }
        latest_info = df.iloc[-1] if len(df) > 0 else None
        return candles, mas, markers, latest_signal, latest_info

    upbit_candles, upbit_mas, markers, latest_signal, latest_info = (
        get_goya_signals(symbol_upbit, target_minutes)
    )

    # ---------------------------------------------------------
    # 4. OHLCV 고가/저가/시가/종가 정보 상세 표시 패널
    # ---------------------------------------------------------
    if latest_info is not None:
        st.markdown("### 📌 실시간 OHLCV 및 시그널 상세 정보")
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("시가 (Open)", f"{latest_info['opening_price']:,} 원")
        m2.metric("고가 (High)", f"{latest_info['high_price']:,} 원")
        m3.metric("저가 (Low)", f"{latest_info['low_price']:,} 원")
        m4.metric("종가 (Close)", f"{latest_info['trade_price']:,} 원")
        m5.metric(
            "Goya Line",
            f"{latest_info['goya_line']:.2f}"
            if pd.notnull(latest_info["goya_line"])
            else "-",
        )
        m6.metric(
            "Smart Line",
            f"{latest_info['smart_line']:.2f}"
            if pd.notnull(latest_info["smart_line"])
            else "-",
        )

    # 차트 구성
    def build_chart_config(candles, ma_dict, markers):
        chart_options = {
            "height": 520,
            "layout": {
                "background": {"type": "solid", "color": "#131722"},
                "textColor": "#d1d4dc",
            },
            "grid": {
                "vertLines": {"color": "#1f2937"},
                "horzLines": {"color": "#1f2937"},
            },
            "timeScale": {"timeVisible": True, "secondsVisible": False},
        }

        series = [
            {
                "type": "Candlestick",
                "data": candles,
                "markers": markers,
                "options": {
                    "upColor": "#26a69a",
                    "downColor": "#ef5350",
                    "borderVisible": False,
                    "wickUpColor": "#26a69a",
                    "wickDownColor": "#ef5350",
                },
            },
            {
                "type": "Line",
                "data": ma_dict["goya"],
                "options": {
                    "color": "#e91e63",
                    "lineWidth": 3,
                    "title": "GOYA LINE",
                },
            },
            {
                "type": "Line",
                "data": ma_dict["smart"],
                "options": {
                    "color": "#ffeb3b",
                    "lineWidth": 2,
                    "title": "Smart Line",
                },
            },
        ]

        return {"chart": chart_options, "series": series}

    if upbit_candles:
        renderLightweightCharts(
            [build_chart_config(upbit_candles, upbit_mas, markers)],
            key=f"chart_{symbol_upbit}_{current_tf}",
        )

    # ---------------------------------------------------------
    # 5. 바이낸스 선물 차트
    # ---------------------------------------------------------
    st.subheader(f"🌐 바이낸스 선물 실시간 ({binance_ticker})")
    tv_intervals = {1: "1", 3: "3", 5: "5", 15: "15", 60: "60", 240: "240"}
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

# 나머지 탭 예시 준비
with category_tabs[1]:
    st.info("💎 프리미엄 시그널 기능 구현 예정 영역입니다.")

with category_tabs[2]:
    st.info("🚀 NEXT 시그널 기능 구현 예정 영역입니다.")

with category_tabs[3]:
    st.info("🚦 신호등 시그널 기능 구현 예정 영역입니다.")
