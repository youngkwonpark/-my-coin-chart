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
# 2. 데이터 수신 (안전한 바이낸스 Spot / 다중 엔드포인트)
# ---------------------------------------------------------
@st.cache_data(ttl=10)
def fetch_chart_data(symbol, interval_str):
    # 차단 우회를 위한 기본 현물 API 주소
    urls = [
        f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval_str}&limit=300",
        f"https://api1.binance.com/api/v3/klines?symbol={symbol}&interval={interval_str}&limit=300",
        f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval_str}&limit=300",
    ]

    res_data = None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
        return None

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

    # 시간대 KST 변환 (UTC+9)
    df["time_kst"] = pd.to_datetime(
        df["open_time"] + (9 * 3600 * 1000), unit="ms"
    )
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)

    # 고야 지표 산출
    df["goya_line"] = df["close"].rolling(20).mean()
    df["smart_line"] = df["close"].rolling(50).mean()

    # 시그널 로직
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
                        "가격": c_p,
                    }
                )
                last_sig = "LONG"
            elif c_p < goya and c_p < smart and last_sig != "SHORT":
                signals.append(
                    {
                        "시간 (KST)": t_kst,
                        "시그널": "🔴 S (SHORT)",
                        "가격": c_p,
                    }
                )
                last_sig = "SHORT"

    return df, signals


data_res = fetch_chart_data(binance_symbol, interval)

if data_res is None:
    st.error(
        "⚠️ 네트워크 통신이 원활하지 않습니다. 잠시 후 다시 새로고침 해주세요."
    )
else:
    df, signals = data_res
    latest = df.iloc[-1]

    # ---------------------------------------------------------
    # 3. 실시간 OHLCV 표기
    # ---------------------------------------------------------
    st.markdown("### 📌 실시간 OHLCV (KST 기준)")
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
    # 4. 차트 표기
    # ---------------------------------------------------------
    st.subheader(f"📈 {selected_coin} 차트")
    chart_df = df.set_index("time_kst")[["close", "goya_line", "smart_line"]]
    chart_df.columns = ["종가(Close)", "GOYA LINE", "Smart Line"]
    st.line_chart(chart_df)

    # ---------------------------------------------------------
    # 5. 시그널 히스토리
    # ---------------------------------------------------------
    st.subheader("🔔 발생한 시그널")
    if signals:
        st.dataframe(pd.DataFrame(reversed(signals)), use_container_width=True)
    else:
        st.info("현재 구간에서 발생한 시그널이 없습니다.")
