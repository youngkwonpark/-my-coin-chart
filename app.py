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
    page_title="Goya Signal Precision Dashboard", page_icon="📈", layout="wide"
)

st.markdown(
    """
    <style>
    .stApp { background-color: #111318; color: #FFFFFF; }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🛡️ GOYA SMART SIGNAL (KST 동기화)")

# ---------------------------------------------------------
# 1. 사이드바 설정
# ---------------------------------------------------------
SYMBOL_MAP = {
    "XRP (리플)": "XRPUSDT",
    "SOL (솔라나)": "SOLUSDT",
    "BTC (비트코인)": "BTCUSDT",
    "ETH (이더리움)": "ETHUSDT",
}

selected_coin = st.sidebar.selectbox(
    "코인 선택", list(SYMBOL_MAP.keys()), index=0
)
binance_symbol = SYMBOL_MAP[selected_coin]

timeframe_map = {
    "1분": "1m",
    "3분": "3m",
    "5분": "5m",
    "15분": "15m",
    "1시간": "1h",
    "4시간": "4h",
}

tf_selected = st.sidebar.radio("타임프레임", list(timeframe_map.keys()), index=4)
interval = timeframe_map[tf_selected]


# ---------------------------------------------------------
# 2. API 차단 우회 및 KST 시간 오차 동기화 함수
# ---------------------------------------------------------
@st.cache_data(ttl=5)
def get_synchronized_data(symbol, interval_str):
    # 접속 차단을 우회하기 위한 다중 엔드포인트
    urls = [
        f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval_str}&limit=300",
        f"https://api1.binance.com/api/v3/klines?symbol={symbol}&interval={interval_str}&limit=300",
        f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval_str}&limit=300",
    ]

    res_data = None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    }

    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=3).json()
            if isinstance(res, list) and len(res) > 0:
                res_data = res
                break
        except Exception:
            continue

    if not res_data:
        return None, None, None, None, None

    df = pd.DataFrame(
        res_data,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "qav",
            "num_trades",
            "tb_base_av",
            "tb_quote_av",
            "ignore",
        ],
    )

    # [핵심] 바이낸스 UTC 시간을 한국 시간(KST, UTC+9) 초 단위로 정확히 동기화
    df["timestamp_kst_sec"] = (df["open_time"] / 1000) + (9 * 3600)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)

    # 고야 라인(20선) 및 스마트 라인(50선) 계산
    df["goya_line"] = df["close"].rolling(20).mean()
    df["smart_line"] = df["close"].rolling(50).mean()

    candles = []
    goya_data, smart_data = [], []
    markers = []
    signals_table = []
    last_sig = None

    for i in range(len(df)):
        row = df.iloc[i]
        t_sec = int(row["timestamp_kst_sec"])

        # KST 기준으로 변환된 날짜/시간 문자열 (시차 오차 없이 정확히 일치)
        dt_kst = datetime.datetime.utcfromtimestamp(t_sec)
        t_kst_str = dt_kst.strftime("%m-%d %H:%M")

        c_p, o_p, h_p, l_p = (
            row["close"],
            row["open"],
            row["high"],
            row["low"],
        )

        candles.append(
            {"time": t_sec, "open": o_p, "high": h_p, "low": l_p, "close": c_p}
        )

        if pd.notnull(row["goya_line"]):
            goya_data.append({"time": t_sec, "value": float(row["goya_line"])})
        if pd.notnull(row["smart_line"]):
            smart_data.append(
                {"time": t_sec, "value": float(row["smart_line"])}
            )

        # 롱 / 숏 시그널 판정 로직
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
                signals_table.append(
                    {
                        "시간 (KST)": t_kst_str,
                        "시그널": "🟢 L (LONG)",
                        "가격": f"{c_p:,.4f}",
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
                signals_table.append(
                    {
                        "시간 (KST)": t_kst_str,
                        "시그널": "🔴 S (SHORT)",
                        "가격": f"{c_p:,.4f}",
                    }
                )
                last_sig = "SHORT"

    mas = {"goya": goya_data, "smart": smart_data}
    latest_info = df.iloc[-1]
    return candles, mas, markers, latest_info, signals_table


data_package = get_synchronized_data(binance_symbol, interval)

if data_package[0] is None:
    st.error(
        "⚠️ 네트워크 통신에 일시적인 지연이 발생했습니다. 잠시 후 새로고침 해주세요."
    )
else:
    candles, mas, markers, latest_info, signals_table = data_package

    # ---------------------------------------------------------
    # 3. 상단 실시간 OHLCV 지표 출력
    # ---------------------------------------------------------
    st.markdown("### 📌 실시간 OHLCV (한국시간 KST 기준)")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("시가 (Open)", f"{latest_info['open']:.4f}")
    c2.metric("고가 (High)", f"{latest_info['high']:.4f}")
    c3.metric("저가 (Low)", f"{latest_info['low']:.4f}")
    c4.metric("종가 (Close)", f"{latest_info['close']:.4f}")
    c5.metric(
        "Goya Line",
        f"{latest_info['goya_line']:.4f}"
        if pd.notnull(latest_info["goya_line"])
        else "-",
    )
    c6.metric(
        "Smart Line",
        f"{latest_info['smart_line']:.4f}"
        if pd.notnull(latest_info["smart_line"])
        else "-",
    )

    # ---------------------------------------------------------
    # 4. 트레이딩뷰 스타일 캔들 차트 (화살표 마커 포함)
    # ---------------------------------------------------------
    st.subheader(f"📈 {selected_coin} 스마트 캔들 차트")

    chart_options = {
        "height": 500,
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
        key=f"chart_{binance_symbol}_{interval}",
    )

    # ---------------------------------------------------------
    # 5. 하단 시그널 히스토리 테이블
    # ---------------------------------------------------------
    st.subheader("🔔 발생한 스마트 시그널 히스토리")
    if signals_table:
        st.dataframe(
            pd.DataFrame(reversed(signals_table)), use_container_width=True
        )
    else:
        st.info("현재 구간에서 발생한 시그널이 없습니다.")
