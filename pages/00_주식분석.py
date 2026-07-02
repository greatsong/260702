import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 페이지 설정 ---
st.set_page_config(
    page_title="글로벌 & 한국 주식 데이터 분석기",
    page_icon="📈",
    layout="wide"
)

st.title("📈 글로벌 & 한국 주식 데이터 분석 웹앱")
st.markdown("""
이 앱은 **Yahoo Finance(yfinance)** 데이터를 활용하여 국내외 주식 시장의 흐름을 분석합니다.
원하는 티커를 입력하고 대화형 그래프로 주가를 확인해보세요!
""")

# --- 사이드바: 입력 제어 ---
st.sidebar.header("🔍 검색 및 설정")

with St.sidebar.expander("💡 티커(Ticker) 입력 가이드", expanded=False):
    st.markdown("""
    - **미국 주식**: Apple (`AAPL`), NVIDIA (`NVDA`), Tesla (`TSLA`)
    - **한국 주식**: 삼성전자 (`005930.KS`), SK하이닉스 (`000660.KS`), 카카오 (`035720.KQ`)
    *코스피는 뒤에 `.KS`, 코스닥은 `.KQ`를 붙여야 합니다.*
    """)

ticker_input = st.sidebar.text_input("주식 Ticker 기호 입력:", value="005930.KS").strip().upper()

start_date = st.sidebar.date_input("시작일", datetime.now() - timedelta(days=365))
end_date = st.sidebar.date_input("종료일", datetime.now())

ma_days = st.sidebar.multiselect(
    "이동평균선(MA) 선택:",
    options=[5, 20, 60, 120],
    default=[5, 20, 60]
)

# --- 데이터 로드 기능 ---
@st.cache_data(ttl=1800)  # 캐싱 시간을 30분으로 조정하여 최신 데이터 반영과 차단 방지 밸런스 유지
def load_data(ticker, start, end):
    try:
        # yfinance의 주가 다운로드는 비교적 차단이 덜합니다.
        data = yf.download(ticker, start=start, end=end)
        return data
    except Exception as e:
        return None

if ticker_input:
    with st.spinner("데이터를 불러오는 중입니다..."):
        df = load_data(ticker_input, start_date, end_date)
    
    if df is not None and not df.empty:
        
        # ⚠️ [수정 포인트] 에러 유발 주범인 .info를 제거하고 논리적으로 메타데이터 처리
        company_name = ticker_input
        
        # 티커 확장자를 보고 통화(Currency) 단위를 수동 추론 (차단 원천 차단)
        if ticker_input.endswith(".KS") or ticker_input.endswith(".KQ"):
            currency = "KRW (원)"
        else:
            currency = "USD ($)"

        # --- 주요 지표 레이아웃 ---
        st.subheader(f"🏢 {company_name} 현재 시장 데이터")
        
        latest_close = df['Close'].iloc[-1].item()
        prev_close = df['Close'].iloc[-2].item() if len(df) > 1 else latest_close
        price_change = latest_close - prev_close
        price_change_pct = (price_change / prev_close) * 100

        col1, col2, col3 = st.columns(3)
        col1.metric(label="최종 종가", value=f"{latest_close:,.2f} {currency}", delta=f"{price_change:,.2f} ({price_change_pct:.2f}%)")
        
        if 'Volume' in df.columns:
            latest_vol = df['Volume'].iloc[-1].item()
            col2.metric(label="최근 거래량", value=f"{latest_vol:,.0f} 주")
        
        # --- 주식 용어 사전 ---
        with st.expander("📚 주식 기초 용어 설명 보기"):
            st.markdown("""
            * **종가 (Close):** 주식 시장이 마감될 때 결정된 최종 가격입니다. 투자자들이 당일 가치를 어떻게 평가했는지 보여주는 가장 중요한 기준입니다.
            * **거래량 (Volume):** 해당 하루 동안 사고판 주식의 총 개수입니다. 거래량이 많을수록 시장의 관심이 뜨겁고, 주가 변동에 신뢰성이 높아집니다.
            * **이동평균선 (Moving Average, MA):** 특정 기간(예: 5일, 20일) 동안의 주가를 평균 내어 선으로 연결한 것입니다. 주가의 방향성(추세)을 매끄럽게 파악하는 데 도움을 줍니다.
            """)

        # --- Plotly 대화형 차트 그리기 ---
        st.subheader("📈 주가 추이 차트")
        
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'].squeeze(),
            high=df['High'].squeeze(),
            low=df['Low'].squeeze(),
            close=df['Close'].squeeze(),
            name="주가 (OHLC)"
        ))

        for ma in ma_days:
            df[f'MA_{ma}'] = df['Close'].rolling(window=ma).mean()
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[f'MA_{ma}'].squeeze(),
                mode='lines',
                name=f'{ma}일 이동평균선'
            ))

        fig.update_layout(
            title=f"{company_name} 주가 분석 (캔들스틱 & 이동평균선)",
            xaxis_title="날짜",
            yaxis_title=f"주가 ({currency})",
            xaxis_rangeslider_visible=True,
            template="plotly_white",
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)

        if st.checkbox("전체 데이터 테이블 보기"):
            st.dataframe(df.sort_index(ascending=False))

    else:
        st.error("데이터를 가져오지 못했습니다. 티커 기호가 정확한지, 혹은 Yahoo Finance 서버가 일시적으로 요청을 제한 중인지 확인해주세요.")
