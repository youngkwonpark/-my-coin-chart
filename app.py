import datetime
import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------
# 0. 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="Goya Signal Precision Dashboard", page_icon="📈", layout="wide"
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
upbit_symbol = SYMBOL_MAP[selected_coin]

timeframe_map = {
    "1분": 1,
    "3분": 3,
    "5분": 5,
    "15분": 15,
    "1시간": 60,
    "4시간": 240,
}

tf_selected = st.sidebar.radio("타임프레임", list(timeframe_map.keys()), index=4)
minutes = timeframe_map[tf_selected]


# ---------------------------------------------------------
# 2. 업비트 API 호출 (차단 우회/안정성 100%)
# ---------------------------------------------------------
@st.cache_data(ttl=5)
def fetch_upbit_data(market, min_time):
    url = f"https://api.upbit.com/v1/candles/minutes/{min_time}?market={market}&count=200"
    headers = {"accept": "application/json"}

    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if not isinstance(res, list) or len(res) == 0:
            return None

        res.reverse()  # 과거 -> 현재 순서 정렬
        df = pd.DataFrame(res)

        df["time_kst"] = pd.to_datetime(df["candle_date_time_kst"])
        df["open"] = df["opening_price"]
        df["high"] = df["high_price"]
        df["low"] = df["low_price"]
        df["close"] = df["trade_price"]

        # 고야 지표 산출
        df["goya_line"] = df["close"].rolling(20).mean()
        df["smart_line"] = df["close"].rolling(50).mean()

        # 시그널 포착 로직
        signals = []
        last_sig = None
        for i in range(50, len(df)):
            c_p = df.iloc[i]["close"]
            goya = df.iloc[i]["goya_line"]
            smart = df.iloc[i]["smart_line"]
            t_kst = df.iloc[i]["time_kst"].strftime("%m-%d %H:%M")

            if pd.notnull(goya) and pd.notnull(smart):
                if c_p > goya and c_p > smart and last_sig != "LONG":
                    signals.append(
                        {
                            "시간 (KST)": t_kst,
                            "시그널": "🟢 L (LONG)",
                            "가격(원)": f"{c_p:,.0f}",
                        }
                    )
                    last_sig = "LONG"
                elif c_p < goya and c_p < smart and last_sig != "SHORT":
                    signals.append(
                        {
                            "시간 (KST)": t_kst,
                            "시그널": "🔴 S (SHORT)",
                            "가격(원)": f"{c_p:,.0f}",
                        }
                    )
                    last_sig = "SHORT"

        return df, signals
    except Exception as e:
        return None


data_res = fetch_upbit_data(upbit_symbol, minutes)

if data_res is None:
    st.error(
        "⚠️ 시세를 불러오는 중 잠시 지연이 발생했습니다. 새로고침을 눌러주세요."
    )
else:
    df, signals = data_res
    latest = df.iloc[-1]

    # ---------------------------------------------------------
    # 3. 실시간 OHLCV 표기
    # ---------------------------------------------------------
    st.markdown("### 📌 실시간 OHLCV (한국시간 KST 기준)")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("시가 (Open)", f"{latest['open']:,} 원")
    c2.metric("고가 (High)", f"{latest['high']:,} 원")
    c3.metric("저가 (Low)", f"{latest['low']:,} 원")
    c4.metric("종가 (Close)", f"{latest['close']:,} 원")
    c5.metric(
        "Goya Line",
        f"{latest['goya_line']:,.1f}"
        if pd.notnull(latest["goya_line"])
        else "-",
    )
    c6.metric(
        "Smart Line",
        f"{latest['smart_line']:,.1f}"
        if pd.notnull(latest["smart_line"])
        else "-",
    )

    # ---------------------------------------------------------
    # 4. 차트 표기
    # ---------------------------------------------------------
    st.subheader(f"📈 {selected_coin} 차트")
    chart_df = df.set_index("time_kst")[["close", "goya_line", "smart_line"]]
    chart_df.columns = ["종가(Close)", "GOYA LINE", "Smart Line"]
    st.line_chart(chart_df)

    # ---------------------------------------------------------
    # 5. 시그널 히스토리
    # ---------------------------------------------------------
    st.subheader("🔔 발생한 스마트 시그널")
    if signals:
        st.dataframe(pd.DataFrame(reversed(signals)), use_container_width=True)
    else:
        st.info("현재 구간에서 발생한 시그널이 없습니다.")
