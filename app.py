import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# 페이지 설정 (반응형 와이드 레이아웃)
st.set_page_config(
    page_title="고야 스마트 프리미엄 차트",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ 고야 스마트 프리미엄 차트 (Pro Signal v3.3)")

# 상단 입력 컨트롤
col1, col2 = st.columns([2, 1])
with col1:
    symbol = st.text_input("코인 심볼 입력 (예: XRPUSDT, BTCUSDT)", value="XRPUSDT").upper().strip()
with col2:
    interval = st.selectbox("시간봉 선택", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3)

@st.cache_data(ttl=30)
def fetch_advanced_data(symbol, interval):
    url_klines = "https://data-api.binance.vision/api/v3/klines"
    url_ticker = "https://data-api.binance.vision/api/v3/ticker/24hr"
    
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": 120  # 모바일 가독성을 위한 최적 캔들 수
    }
    
    try:
        res_klines = requests.get(url_klines, params=params, timeout=5)
        if res_klines.status_code != 200:
            return None, None
        data = res_klines.json()
        
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
        res_ticker = requests.get(url_ticker, params={"symbol": symbol}, timeout=5)
        ticker_data = res_ticker.json() if res_ticker.status_code == 200 else {}
        
        return df, ticker_data
    except Exception as e:
        return None, None

# 데이터 로드
df, ticker = fetch_advanced_data(symbol, interval)

if df is not None and not df.empty:
    st.success(f"성공적으로 {symbol} ({interval}) 매크로 데이터를 동기화했습니다!")
    
    # --- [섹션 1] 매크로 시그널 & 청산/고래 동향 분석 패널 ---
    st.markdown("### 📊 실시간 온체인 및 오더플로우 매크로 시그널")
    
    recent_df = df.tail(20)
    total_vol = float(recent_df['volume'].sum())
    buy_vol = float(recent_df['taker_buy_base_asset_volume'].sum())
    sell_vol = max(0.0, total_vol - buy_vol)
    
    buy_ratio = (buy_vol / total_vol * 100) if total_vol > 0 else 50.0
    sell_ratio = 100.0 - buy_ratio
    
    col_sig1, col_sig2, col_sig3 = st.columns(3)
    
    with col_sig1:
        if buy_ratio > 55:
            st.metric(label="매수/매도 세력 균형", value="매수 우세 (Bullish)", delta=f"+{buy_ratio-50:.1f}%")
        elif sell_ratio > 55:
            st.metric(label="매수/매도 세력 균형", value="매도 우세 (Bearish)", delta=f"-{sell_ratio-50:.1f}%", delta_color="inverse")
        else:
            st.metric(label="매수/매도 세력 균형", value="중립 횡보 (Neutral)", delta="0.0%")
            
    with col_sig2:
        avg_vol = float(df['volume'].mean())
        latest_vol = float(df.iloc[-1]['volume'])
        if latest_vol > avg_vol * 2.5:
            st.metric(label="고래/대형 거래소 움직임", value="대량 거래 포착 (Whale Active)", delta="주의")
        else:
            st.metric(label="고래/대형 거래소 움직임", value="정상 유동성 흐름", delta="안정")
            
    with col_sig3:
        high_max = float(df['high'].max())
        low_min = float(df['low'].min())
        st.metric(label="핵심 청산 맵 예상 구간", value=f"상단: {high_max:,.2f}", delta=f"하단: {low_min:,.2f}")

    st.markdown("---")

    # --- [섹션 2] 트레이딩뷰 스타일 모바일 최적화 인터랙티브 차트 ---
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=symbol,
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350'
    ))

    # 모바일 터치 시 캔들 찢어짐 및 비율 깨짐 방지를 위한 레이아웃 고정 설정
    fig.update_layout(
        title=dict(text=f"{symbol} Pro Interactive Chart ({interval})", font=dict(size=15)),
        yaxis_title="USDT Price",
        xaxis_rangeslider_visible=False,
        height=500,
        margin=dict(l=5, r=5, t=30, b=5),
        hovermode="x unified",
        template="plotly_dark",
        dragmode="zoom"  # 드래그 시 왜곡 없이 부드러운 줌인/아웃 지원
    )
    
    # 축 고정 설정을 통해 강제로 캔들 모양 유지
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(255,255,255,0.1)',
        fixedrange=False
    )
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(255,255,255,0.1)',
        side="right",
        fixedrange=False,
        autorange=True
    )

    # 설정 적용하여 스트림릿에 출력 (반응형 너비 고정)
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})
else:
    st.error("코인 데이터를 불러오지 못했습니다. 심볼명을 다시 확인해 주세요.")
