import datetime
import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------
# 0. 기본 설정 및 기본 테마
# ---------------------------------------------------------
st.set_page_config(
    page_title="Goya Signal Precision Dashboard", page_icon="📈", layout="wide"
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
# 2. 바이낸스 선물 API 안전 호출
# ---------------------------------------------------------
@st.cache_data(ttl=10)
def get_binance_data(symbol, interval_str):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval_str}&limit=300"
    try:
        res = requests.get(url, timeout=5).json()
        if not isinstance(res, list) or len(res) == 0:
            return None
        df = pd.DataFrame(
            res,
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

        # 시간대 KST 변환 (UTC+9)
        df["time_kst"] = pd.to_datetime(
            df["open_time"] + (9 * 3600 * 1000), unit="ms"
        )
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)

        # 지표 계산
        df["goya_line"] = df["close"].rolling(20).mean()
        df["smart_line"] = df["close"].rolling(50).mean()

        # 시그널 추출
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
                            "time": t_kst,
                            "type": "L (LONG)",
                            "price": c_p,
                            "color": "🟢",
                        }
                    )
                    last_sig = "LONG"
                elif c_p < goya and c_p < smart and last_sig != "SHORT":
                    signals.append(
                        {
                            "time": t_kst,
                            "type": "S (SHORT)",
                            "price": c_p,
                            "color": "🔴",
                        }
                    )
                    last_sig = "SHORT"

        return df, signals
    except Exception as e:
        return None


data_res = get_binance_data(binance_symbol, interval)

if data_res is None:
    st.error(
        "⚠️ 바이낸스 API 응답을 불러오는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
    )
else:
    df, signals = data_res
    latest = df.iloc[-1]

    # ---------------------------------------------------------
    # 3. 실시간 OHLCV 지표 출력
    # ---------------------------------------------------------
    st.markdown("### 📌 실시간 OHLCV (한국시간 KST 기준)")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("시가 (Open)", f"{latest['open']:.4f}")
    c2.metric("고가 (High)", f"{latest['high']:.4f}")
    c3.metric("저가 (Low)", f"{latest['low']:.4f}")
    c4.metric("종가 (Close)", f"{latest['close']:.4f}")
    c5.metric(
        "Goya Line",
        f"{latest['goya_line']:.4f}"
        if pd.notnull(latest["goya_line"])
        else "-",
    )
    c6.metric(
        "Smart Line",
        f"{latest['smart_line']:.4f}"
        if pd.notnull(latest["smart_line"])
        else "-",
    )

    # ---------------------------------------------------------
    # 4. 차트 표현 (Streamlit 기본 Line Chart)
    # ---------------------------------------------------------
    st.subheader(f"📈 {selected_coin} 가격 & 고야 지표")
    chart_df = df.set_index("time_kst")[["close", "goya_line", "smart_line"]]
    chart_df.columns = ["종가(Close)", "GOYA LINE", "Smart Line"]
    st.line_chart(chart_df)

    # ---------------------------------------------------------
    # 5. 포착된 시그널 히스토리
    # ---------------------------------------------------------
    st.subheader("🔔 포착된 스마트 시그널 목록 (최근순)")
    if signals:
        sig_df = pd.DataFrame(reversed(signals))
        st.dataframe(sig_df, use_container_width=True)
    else:
        st.info("현재 구간에서 발생한 시그널이 없습니다.")
