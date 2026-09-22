import datetime
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit_lightweight_charts import renderLightweightCharts

# ---------------------------------------------------------
# 0. 기본 설정 및 다크 테마
# ---------------------------------------------------------
st.set_page_config(
    page_title="Goya Signal Precision Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #111318; color: #FFFFFF; }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🛡️ GOYA SMART SIGNAL & BINANCE INTEGRATION")

# ---------------------------------------------------------
# 1. 사이드바 설정 (코인 선택 및 타임프레임)
# ---------------------------------------------------------
st.sidebar.header("🎛️ 차트 제어 패널")

SYMBOL_MAP = {
    "XRP (리플)": {"upbit": "KRW-XRP", "binance": "XRP"},
    "SOL (솔라나)": {"upbit": "KRW-SOL", "binance": "SOL"},
    "BTC (비트코인)": {"upbit": "KRW-BTC", "binance": "BTC"},
    "ETH (이더리움)": {"upbit": "KRW-ETH", "binance": "ETH"},
}

coin_list = list(SYMBOL_MAP.keys())
selected_coin = st.sidebar.selectbox("🪙 코인 선택", coin_list, index=0)

market_code = SYMBOL_MAP[selected_coin]["upbit"]
binance_ticker = SYMBOL_MAP[selected_coin]["binance"]

timeframe_map = {
    "1분": {"upbit": "minutes/1", "tv": "1"},
    "3분": {"upbit": "minutes/3", "tv": "3"},
    "5분": {"upbit": "minutes/5", "tv": "5"},
    "15분": {"upbit": "minutes/15", "tv": "15"},
    "1시간": {"upbit": "minutes/60", "tv": "60"},
    "4시간": {"upbit": "minutes/240", "tv": "240"},
}

tf_selected = st.sidebar.radio("⏱️ 타임프레임 선택", list(timeframe_map.keys()), index=4)
tf_path = timeframe_map[tf_selected]["upbit"]
tv_interval = timeframe_map[tf_selected]["tv"]


# ---------------------------------------------------------
# 2. 데이터 수집 및 KST 시간 축 왜곡 원인 차단
# ---------------------------------------------------------
@st.cache_data(ttl=5)
def get_chart_data(market, tf):
    url = f"https://api.upbit.com/v1/candles/{tf}?market={market}&count=200"
    headers = {"accept": "application/json"}

    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if not isinstance(res, list) or len(res) == 0:
            return None, None, None, None

        res.reverse()  # 과거 -> 현재 순서로 정렬
        df = pd.DataFrame(res)

        # [핵심] KST 문자열을 완벽하게 인식시켜 1970년 오류 및 시간 밀림 현상 방지
        dt_kst = pd.to_datetime(df["candle_date_time_kst"])
        df["time"] = (
            dt_kst.dt.tz_localize("Asia/Seoul")
            .dt.tz_convert("UTC")
            .astype("int64")
            // 10**9
        )
        df["dt_str"] = dt_kst.dt.strftime("%m-%d %H:%M")

        df["open"] = df["opening_price"]
        df["high"] = df["high_price"]
        df["low"] = df["low_price"]
        df["close"] = df["trade_price"]

        # 이동평균선 계산 (고야라인 20선, 스마트라인 50선)
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

    # ---------------------------------------------------------
    # 3. 차트 좌측 상단 스타일의 실시간 OHLCV 오버레이 구현
    # ---------------------------------------------------------
    st.subheader(f"📈 {selected_coin} 업비트 스마트 캔들 차트")

    # 고야 차트처럼 마우스 오버 또는 최신 바의 상세 정보를 보여주는 좌측 상단 박스 스타일 적용
    st.markdown(
        f"""
        <div style="background-color: #1e222d; padding: 10px 15px; border-radius: 6px; font-family: monospace; font-size: 14px; margin-bottom: 10px; border: 1px solid #2a2e39;">
            <span style="color: #ffeb3b; font-weight: bold;">{selected_coin}</span> &nbsp;|&nbsp; 
            <span style="color: #9aca3c;">🕒 {latest_info['candle_date_time_kst']}</span><br>
            <span style="color: #d1d4dc;">O: <b>{latest_info['open']:,}</b></span> &nbsp;
            <span style="color: #26a69a;">H: <b>{latest_info['high']:,}</b></span> &nbsp;
            <span style="color: #ef5350;">L: <b>{latest_info['low']:,}</b></span> &nbsp;
            <span style="color: #2196f3;">C: <b>{latest_info['close']:,}</b></span> &nbsp;
            <span style="color: #e91e63;">Goya: <b>{latest_info['goya_line']:,.1f}</b></span> &nbsp;
            <span style="color: #ffeb3b;">Smart: <b>{latest_info['smart_line']:,.1f}</b></span>
        </div>
    """,
        unsafe_allow_html=True,
    )

    chart_options = {
        "height": 480,
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

    # ---------------------------------------------------------
    # 4. 바이낸스 실시간 연동 차트 (하단)
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader(
        f"🌐 바이낸스 실시간 연동 차트 ({binance_ticker} / USDT Perpetual)"
    )

    binance_html = f"""
    <div class="tradingview-widget-container" style="height:500px;width:100%">
      <div id="tradingview_binance" style="height:100%;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "autosize": true,
        "symbol": "BINANCE:{binance_ticker}USDT",
        "interval": "{tv_interval}",
        "timezone": "Asia/Seoul",
        "theme": "dark",
        "style": "1",
        "locale": "kr",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_binance"
      }});
      </script>
    </div>
    """
    components.html(binance_html, height=520)
