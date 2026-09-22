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
    "XRP (리플)": "KRW-XRP",
    "SOL (솔라나)": "KRW-SOL",
    "BTC (비트코인)": "KRW-BTC",
    "ETH (이더리움)": "KRW-ETH",
}

selected_coin = st.sidebar.selectbox(
    "코인 선택", list(SYMBOL_MAP.keys()), index=0
)
market_code = SYMBOL_MAP[selected_coin]

timeframe_map = {
    "1분": "minutes/1",
    "3분": "minutes/3",
    "5분": "minutes/5",
    "15분": "minutes/15",
    "1시간": "minutes/60",
    "4시간": "minutes/240",
}

tf_selected = st.sidebar.radio("타임프레임", list(timeframe_map.keys()), index=4)
tf_path = timeframe_map[tf_selected]


# ---------------------------------------------------------
# 2. 데이터 안전 수집 및 가공
# ---------------------------------------------------------
@st.cache_data(ttl=5)
def get_chart_data(market, tf):
    url = f"https://api.upbit.com/v1/candles/{tf}?market={market}&count=200"
    headers = {"accept": "application/json"}

    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if not isinstance(res, list) or len(res) == 0:
            return None, None, None, None, None

        df = pd.DataFrame(res)
        df.reverse_df = df.iloc[::-1].reset_index(
            drop=True
        )  # 과거 -> 현재 정렬
        df = df.iloc[::-1].reset_index(drop=True)

        # 시간 변환 (타임스탬프 초 단위 정수형)
        df["dt"] = pd.to_datetime(df["candle_date_time_kst"])
        df["time"] = df["dt"].astype("int64") // 10**9

        df["open"] = df["opening_price"]
        df["high"] = df["high_price"]
        df["low"] = df["low_price"]
        df["close"] = df["trade_price"]

        # 이동평균선 계산
        df["goya_line"] = df["close"].rolling(20).mean()
        df["smart_line"] = df["close"].rolling(50).mean()

        candles = []
        goya_data, smart_data = [], []
        markers = []
        signals_table = []
        last_sig = None

        for i in range(len(df)):
            row = df.iloc[i]
            t_sec = int(row["time"])
            t_kst_str = row["dt"].strftime("%m-%d %H:%M")

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
                    signals_table.append(
                        {
                            "시간 (KST)": t_kst_str,
                            "시그널": "🟢 L (LONG)",
                            "가격": f"{c_p:,.0f} 원",
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
                            "가격": f"{c_p:,.0f} 원",
                        }
                    )
                    last_sig = "SHORT"

        mas = {"goya": goya_data, "smart": smart_data}
        latest_info = df.iloc[-1]
        return candles, mas, markers, latest_info, signals_table
    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생: {e}")
        return None, None, None, None, None


data_package = get_chart_data(market_code, tf_path)

if data_package[0] is None:
    st.warning("데이터를 불러오는 중입니다...")
else:
    candles, mas, markers, latest_info, signals_table = data_package

    # ---------------------------------------------------------
    # 3. 상단 실시간 OHLCV 지표 출력
    # ---------------------------------------------------------
    st.markdown("### 📌 실시간 OHLCV (한국시간 KST 기준)")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("시가 (Open)", f"{latest_info['open']:,} 원")
    c2.metric("고가 (High)", f"{latest_info['high']:,} 원")
    c3.metric("저가 (Low)", f"{latest_info['low']:,} 원")
    c4.metric("종가 (Close)", f"{latest_info['close']:,} 원")
    c5.metric(
        "Goya Line",
        f"{latest_info['goya_line']:,.1f}"
        if pd.notnull(latest_info["goya_line"])
        else "-",
    )
    c6.metric(
        "Smart Line",
        f"{latest_info['smart_line']:,.1f}"
        if pd.notnull(latest_info["smart_line"])
        else "-",
    )

    # ---------------------------------------------------------
    # 4. 캔들 차트 출력
    # ---------------------------------------------------------
    st.subheader(f"📈 {selected_coin} 스마트 캔들 차트")

    chart_options = {
        "height": 500,
        "layout": {"background": {"color": "#131722"}, "textColor": "#d1d4dc"},
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
        key=f"chart_{market_code}_{tf_path}",
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
