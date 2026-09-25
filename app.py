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
    # 바이낸스 공식 데이터 엔드포인트
    url_klines = "https://data-api.binance.vision/api/v3/klines"
    url_ticker = "https://data-api.binance.vision/api/v3/ticker/24hr"
    
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": 150  # 더 넉넉한 캔들 데이터 로드
    }
    
    try:
        # 1. 캔들 데이터 가져오기
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
        for col in ['open', 'high', 'low', 'close', 'volume', 'taker_buy_quote_asset_volume', 'quote_asset_volume']:
            df[col] = df[col].astype(float)
            
        # 2. 24시간 통계 및 매수/매도 볼륨 분석 (고래/오더플로우 매크로 시뮬레이션)
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
    
    # 최근 봉들의 테이커 매수/매도 볼륨 비교를 통한 강도 계산
    recent_df = df.tail(20)
    total_vol = recent_df['volume'].sum()
    buy_vol = recent_df['taker_buy_base_asset_volume'].sum()
    sell_vol = total_vol - buy_vol
    
    buy_ratio = (buy_vol / total_vol * 100) if total_vol > 0 else 50
    sell_ratio = 100 - buy_ratio
    
    col_sig1, col_sig2, col_sig3 = st.columns(3)
    
    with col_sig1:
        if buy_ratio > 55:
            st.metric(label="매수/매도 세력 균형", value="매수 우세 (Bullish)", delta=f"+{buy_ratio-50:.1f}%")
        elif sell_ratio > 55:
            st.metric(label="매수/매도 세력 균형", value="매도 우세 (Bearish)", delta=f"-{sell_ratio-50:.1f}%", delta_color="inverse")
        else:
            st.metric(label="매수/매도 세력 균형", value="중립 횡보 (Neutral)", delta="0.0%")
            
    with col_sig2:
        # 변동성 및 고래 거래량 감지 시뮬레이션
        avg_vol = df['volume'].mean()
        latest_vol = df.iloc[-1]['volume']
        if latest_vol > avg_vol * 2.5:
            st.metric(label="고래/대형 거래소 움직임", value="대량 거래 포착 (Whale Active)", delta="주의")
        else:
            st.metric(label="고래/대형 거래소 움직임", value="정상 유동성 흐름", delta="안정")
            
    with col_sig3:
        # 가상 청산 맵 매크로 레벨 계산 (최근 고저가 기준)
        high_max = df['high'].max()
        low_min = df['low'].min()
        st.metric(label="핵심 청산 맵 예상 구간", value=f"상단: {high_max:,.2f}", delta=f"하단: {low_min:,.2f}")

    st.markdown("---")

    # --- [섹션 2] 트레이딩뷰 스타일 개선형 인터랙티브 차트 ---
    fig = go.Figure()

    # 캔들스틱 추가 (호버 시 상세 데이터 및 줌/팬 최적화)
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=symbol,
        increasing_line_color='#26a69a', # 상승 캔들 색상 (초록)
        decreasing_line_color='#ef5350'  # 하락 캔들 색상 (빨강)
    ))

    # 레이아웃 모바일 최적화 및 인터랙션 강화 (마우스 호버 시 툴팁 고정, 줌/팬 활성화)
    fig.update_layout(
        title=dict(text=f"{symbol} Pro Interactive Chart ({interval})", font=dict(size=16)),
        yaxis_title="USDT Price",
        xaxis_rangeslider_visible=False,
        height=550,
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x unified",  # 마우스 올렸을 때 해당 시간의 모든 데이터 한눈에 보기
        template="plotly_dark"   # 다비 모드 스타일 적용으로 시인성 극대화
    )
    
    # x축/y축 스케일러블 설정
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(255,255,255,0.1)'
    )
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(255,255,255,0.1)',
        side="right"
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("코인 데이터를 불러오지 못했습니다. 심볼명을 다시 확인해 주세요.")
