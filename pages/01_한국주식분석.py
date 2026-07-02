import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, timedelta

st.set_page_config(
    page_title="글로벌 · 한국 주식 데이터 분석 웹앱",
    page_icon="📈",
    layout="wide"
)

# -------------------------------------------------
# 기본 설정
# -------------------------------------------------

DEFAULT_TICKERS = {
    "한국 대표 주식": {
        "삼성전자": "005930.KS",
        "SK하이닉스": "000660.KS",
        "현대차": "005380.KS",
        "LG에너지솔루션": "373220.KS",
        "NAVER": "035420.KS",
        "카카오": "035720.KS",
        "셀트리온": "068270.KS",
    },
    "미국 대표 주식": {
        "Apple": "AAPL",
        "Microsoft": "MSFT",
        "NVIDIA": "NVDA",
        "Tesla": "TSLA",
        "Google": "GOOGL",
        "Amazon": "AMZN",
        "Meta": "META",
    },
    "글로벌 ETF": {
        "S&P500 ETF": "SPY",
        "NASDAQ100 ETF": "QQQ",
        "미국 전체시장 ETF": "VTI",
        "미국 장기채 ETF": "TLT",
        "금 ETF": "GLD",
        "원유 ETF": "USO",
    },
    "한국 지수": {
        "KOSPI": "^KS11",
        "KOSDAQ": "^KQ11",
    },
    "미국 지수": {
        "S&P500": "^GSPC",
        "NASDAQ": "^IXIC",
        "Dow Jones": "^DJI",
    }
}


# -------------------------------------------------
# 데이터 함수
# -------------------------------------------------

@st.cache_data(ttl=3600)
def load_stock_data(tickers, start_date, end_date):
    data = yf.download(
        tickers=tickers,
        start=start_date,
        end=end_date,
        auto_adjust=False,
        progress=False,
        group_by="ticker"
    )
    return data


def get_price_data(raw_data, ticker):
    """
    yfinance 결과가 단일 종목/복수 종목일 때 모두 처리
    """
    if isinstance(raw_data.columns, pd.MultiIndex):
        df = raw_data[ticker].copy()
    else:
        df = raw_data.copy()

    df = df.dropna()
    return df


def calculate_indicators(df):
    df = df.copy()

    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["MA60"] = df["Close"].rolling(window=60).mean()
    df["MA120"] = df["Close"].rolling(window=120).mean()

    df["Daily Return"] = df["Close"].pct_change()
    df["Cumulative Return"] = (1 + df["Daily Return"]).cumprod() - 1

    rolling_max = df["Close"].cummax()
    df["Drawdown"] = df["Close"] / rolling_max - 1

    return df


def calculate_summary(df):
    df = df.dropna().copy()

    if len(df) < 2:
        return {
            "current_price": np.nan,
            "total_return": np.nan,
            "annual_volatility": np.nan,
            "max_drawdown": np.nan,
            "cagr": np.nan,
        }

    current_price = df["Close"].iloc[-1]
    start_price = df["Close"].iloc[0]
    total_return = current_price / start_price - 1

    daily_return = df["Close"].pct_change().dropna()
    annual_volatility = daily_return.std() * np.sqrt(252)

    rolling_max = df["Close"].cummax()
    drawdown = df["Close"] / rolling_max - 1
    max_drawdown = drawdown.min()

    days = (df.index[-1] - df.index[0]).days
    years = days / 365 if days > 0 else np.nan

    if years and years > 0:
        cagr = (current_price / start_price) ** (1 / years) - 1
    else:
        cagr = np.nan

    return {
        "current_price": current_price,
        "total_return": total_return,
        "annual_volatility": annual_volatility,
        "max_drawdown": max_drawdown,
        "cagr": cagr,
    }


def format_percent(value):
    if pd.isna(value):
        return "-"
    return f"{value * 100:.2f}%"


def format_price(value):
    if pd.isna(value):
        return "-"
    return f"{value:,.2f}"


# -------------------------------------------------
# 화면 제목
# -------------------------------------------------

st.title("📈 글로벌 · 한국 주식 데이터 분석 웹앱")
st.caption(
    "yfinance로 주가 데이터를 불러오고, Plotly로 인터랙티브 차트를 그리는 Streamlit 웹앱입니다."
)

st.warning(
    "이 웹앱은 투자 교육 및 데이터 분석 실습용입니다. "
    "특정 종목의 매수·매도 추천이 아니며, 투자 판단은 본인의 책임입니다."
)


# -------------------------------------------------
# 사이드바
# -------------------------------------------------

st.sidebar.header("⚙️ 분석 설정")

market_group = st.sidebar.selectbox(
    "분석할 시장/그룹 선택",
    list(DEFAULT_TICKERS.keys())
)

selected_names = st.sidebar.multiselect(
    "종목 선택",
    list(DEFAULT_TICKERS[market_group].keys()),
    default=list(DEFAULT_TICKERS[market_group].keys())[:3]
)

custom_tickers = st.sidebar.text_input(
    "직접 티커 입력",
    placeholder="예: AAPL, MSFT, 005930.KS"
)

st.sidebar.caption(
    """
    한국 주식은 보통 뒤에 `.KS` 또는 `.KQ`를 붙입니다.  
    예: 삼성전자 `005930.KS`, 카카오 `035720.KS`
    """
)

period_option = st.sidebar.selectbox(
    "분석 기간",
    ["최근 1개월", "최근 3개월", "최근 6개월", "최근 1년", "최근 3년", "최근 5년", "직접 선택"],
    index=3
)

today = date.today()

if period_option == "최근 1개월":
    start_date = today - timedelta(days=30)
elif period_option == "최근 3개월":
    start_date = today - timedelta(days=90)
elif period_option == "최근 6개월":
    start_date = today - timedelta(days=180)
elif period_option == "최근 1년":
    start_date = today - timedelta(days=365)
elif period_option == "최근 3년":
    start_date = today - timedelta(days=365 * 3)
elif period_option == "최근 5년":
    start_date = today - timedelta(days=365 * 5)
else:
    start_date = st.sidebar.date_input("시작일", today - timedelta(days=365))

end_date = st.sidebar.date_input("종료일", today)

chart_type = st.sidebar.radio(
    "차트 유형",
    ["선 차트", "캔들 차트"],
    horizontal=True
)

show_volume = st.sidebar.checkbox("거래량 함께 보기", value=True)
show_ma = st.sidebar.checkbox("이동평균선 보기", value=True)

selected_tickers = [DEFAULT_TICKERS[market_group][name] for name in selected_names]

if custom_tickers.strip():
    custom_list = [ticker.strip().upper() for ticker in custom_tickers.split(",") if ticker.strip()]
    selected_tickers.extend(custom_list)

selected_tickers = list(dict.fromkeys(selected_tickers))


# -------------------------------------------------
# 데이터 로딩
# -------------------------------------------------

if not selected_tickers:
    st.info("왼쪽 사이드바에서 분석할 종목을 선택하거나 직접 티커를 입력해주세요.")
    st.stop()

try:
    raw_data = load_stock_data(selected_tickers, start_date, end_date + timedelta(days=1))
except Exception as e:
    st.error("데이터를 불러오는 중 오류가 발생했습니다.")
    st.exception(e)
    st.stop()

if raw_data.empty:
    st.error("데이터가 없습니다. 티커 또는 기간을 다시 확인해주세요.")
    st.stop()


# -------------------------------------------------
# 탭 구성
# -------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 개별 종목 분석", "📈 종목 비교", "📋 데이터 표", "📚 주식 용어 설명"]
)


# -------------------------------------------------
# 탭 1. 개별 종목 분석
# -------------------------------------------------

with tab1:
    st.subheader("📊 개별 종목 분석")

    selected_single_ticker = st.selectbox(
        "자세히 볼 종목 선택",
        selected_tickers
    )

    df = get_price_data(raw_data, selected_single_ticker)

    if df.empty:
        st.error("선택한 종목의 데이터가 없습니다.")
        st.stop()

    df = calculate_indicators(df)
    summary = calculate_summary(df)

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("현재 종가", format_price(summary["current_price"]))
    col2.metric("전체 수익률", format_percent(summary["total_return"]))
    col3.metric("연평균 수익률 CAGR", format_percent(summary["cagr"]))
    col4.metric("연환산 변동성", format_percent(summary["annual_volatility"]))
    col5.metric("최대 낙폭 MDD", format_percent(summary["max_drawdown"]))

    if show_volume:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            row_heights=[0.7, 0.3],
            subplot_titles=("가격", "거래량")
        )
    else:
        fig = go.Figure()

    if chart_type == "캔들 차트":
        if show_volume:
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df["Open"],
                    high=df["High"],
                    low=df["Low"],
                    close=df["Close"],
                    name="캔들"
                ),
                row=1,
                col=1
            )
        else:
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df["Open"],
                    high=df["High"],
                    low=df["Low"],
                    close=df["Close"],
                    name="캔들"
                )
            )
    else:
        if show_volume:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["Close"],
                    mode="lines",
                    name="종가"
                ),
                row=1,
                col=1
            )
        else:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["Close"],
                    mode="lines",
                    name="종가"
                )
            )

    if show_ma:
        for ma_col in ["MA20", "MA60", "MA120"]:
            if show_volume:
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df[ma_col],
                        mode="lines",
                        name=ma_col
                    ),
                    row=1,
                    col=1
                )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df[ma_col],
                        mode="lines",
                        name=ma_col
                    )
                )

    if show_volume:
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["Volume"],
                name="거래량"
            ),
            row=2,
            col=1
        )

    fig.update_layout(
        title=f"{selected_single_ticker} 주가 차트",
        xaxis_title="날짜",
        yaxis_title="가격",
        hovermode="x unified",
        height=700,
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📉 누적 수익률과 낙폭")

    fig_return = go.Figure()

    fig_return.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Cumulative Return"] * 100,
            mode="lines",
            name="누적 수익률"
        )
    )

    fig_return.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Drawdown"] * 100,
            mode="lines",
            name="낙폭"
        )
    )

    fig_return.update_layout(
        title="누적 수익률과 낙폭",
        xaxis_title="날짜",
        yaxis_title="비율 (%)",
        hovermode="x unified",
        height=500
    )

    st.plotly_chart(fig_return, use_container_width=True)


# -------------------------------------------------
# 탭 2. 종목 비교
# -------------------------------------------------

with tab2:
    st.subheader("📈 종목 비교")

    comparison_data = pd.DataFrame()
    summary_rows = []

    for ticker in selected_tickers:
        temp_df = get_price_data(raw_data, ticker)

        if temp_df.empty:
            continue

        temp_df = calculate_indicators(temp_df)

        normalized = temp_df["Close"] / temp_df["Close"].iloc[0] * 100
        comparison_data[ticker] = normalized

        summary = calculate_summary(temp_df)
        summary_rows.append({
            "티커": ticker,
            "현재 종가": summary["current_price"],
            "전체 수익률": summary["total_return"],
            "연평균 수익률 CAGR": summary["cagr"],
            "연환산 변동성": summary["annual_volatility"],
            "최대 낙폭 MDD": summary["max_drawdown"],
        })

    if comparison_data.empty:
        st.error("비교할 수 있는 데이터가 없습니다.")
    else:
        fig_compare = go.Figure()

        for ticker in comparison_data.columns:
            fig_compare.add_trace(
                go.Scatter(
                    x=comparison_data.index,
                    y=comparison_data[ticker],
                    mode="lines",
                    name=ticker
                )
            )

        fig_compare.update_layout(
            title="종목별 정규화 수익률 비교",
            xaxis_title="날짜",
            yaxis_title="시작일 = 100 기준",
            hovermode="x unified",
            height=600
        )

        st.plotly_chart(fig_compare, use_container_width=True)

        st.info(
            """
            위 그래프는 모든 종목의 시작점을 100으로 맞춘 뒤 비교한 것입니다.  
            가격 단위가 다른 삼성전자, 애플, ETF 등을 같은 기준에서 비교할 수 있습니다.
            """
        )

        summary_df = pd.DataFrame(summary_rows)

        display_df = summary_df.copy()
        display_df["현재 종가"] = display_df["현재 종가"].map(lambda x: f"{x:,.2f}")
        for col in ["전체 수익률", "연평균 수익률 CAGR", "연환산 변동성", "최대 낙폭 MDD"]:
            display_df[col] = display_df[col].map(lambda x: f"{x * 100:.2f}%" if pd.notna(x) else "-")

        st.markdown("### 📋 종목별 핵심 지표")
        st.dataframe(display_df, use_container_width=True)

        fig_bar = go.Figure()

        fig_bar.add_trace(
            go.Bar(
                x=summary_df["티커"],
                y=summary_df["전체 수익률"] * 100,
                name="전체 수익률"
            )
        )

        fig_bar.update_layout(
            title="종목별 전체 수익률 비교",
            xaxis_title="티커",
            yaxis_title="전체 수익률 (%)",
            height=500
        )

        st.plotly_chart(fig_bar, use_container_width=True)


# -------------------------------------------------
# 탭 3. 데이터 표
# -------------------------------------------------

with tab3:
    st.subheader("📋 원본 데이터 및 다운로드")

    data_ticker = st.selectbox(
        "데이터를 확인할 종목",
        selected_tickers,
        key="table_ticker"
    )

    table_df = get_price_data(raw_data, data_ticker)
    table_df = calculate_indicators(table_df)

    st.dataframe(table_df.tail(300), use_container_width=True)

    csv = table_df.to_csv(index=True).encode("utf-8-sig")

    st.download_button(
        label="CSV 다운로드",
        data=csv,
        file_name=f"{data_ticker}_stock_data.csv",
        mime="text/csv"
    )


# -------------------------------------------------
# 탭 4. 주식 용어 설명
# -------------------------------------------------

with tab4:
    st.subheader("📚 주식 데이터 분석 용어 설명")

    st.markdown(
        """
        ## 1. 시가 Open
        하루 중 주식시장이 열렸을 때 처음 거래된 가격입니다.  
        예를 들어 오전 9시에 장이 시작되고 첫 거래가 70,000원에 체결되었다면 시가는 70,000원입니다.

        ## 2. 고가 High
        하루 동안 거래된 가격 중 가장 높은 가격입니다.  
        그날 사람들이 가장 비싸게 거래한 가격이라고 볼 수 있습니다.

        ## 3. 저가 Low
        하루 동안 거래된 가격 중 가장 낮은 가격입니다.  
        그날 사람들이 가장 싸게 거래한 가격입니다.

        ## 4. 종가 Close
        하루 장이 끝날 때 마지막으로 거래된 가격입니다.  
        주식 분석에서는 보통 종가를 가장 많이 사용합니다.

        ## 5. 거래량 Volume
        하루 동안 거래된 주식 수입니다.  
        거래량이 많다는 것은 그 종목에 대한 시장의 관심이 크다는 뜻일 수 있습니다.

        ## 6. 이동평균선 Moving Average
        일정 기간의 평균 가격을 선으로 나타낸 것입니다.

        - MA20: 최근 20거래일 평균 가격
        - MA60: 최근 60거래일 평균 가격
        - MA120: 최근 120거래일 평균 가격

        이동평균선은 주가의 큰 흐름을 볼 때 사용합니다.  
        단기 가격은 많이 흔들리지만, 평균선을 보면 흐름을 조금 더 부드럽게 볼 수 있습니다.

        ## 7. 수익률 Return
        내가 산 가격에 비해 현재 가격이 얼마나 올랐거나 내렸는지를 나타냅니다.

        예를 들어 10,000원에 산 주식이 12,000원이 되었다면 수익률은 20%입니다.

        계산식은 다음과 같습니다.

        ```
        수익률 = 현재 가격 / 시작 가격 - 1
        ```

        ## 8. 누적 수익률 Cumulative Return
        분석 기간 전체 동안 가격이 얼마나 변했는지를 보여줍니다.  
        시작일을 기준으로 지금까지 얼마나 올랐는지, 또는 떨어졌는지 확인할 수 있습니다.

        ## 9. CAGR 연평균 수익률
        Compound Annual Growth Rate의 약자입니다.  
        전체 기간의 수익률을 1년 단위 평균 성장률로 바꾼 값입니다.

        예를 들어 3년 동안 60% 올랐다고 해서 매년 20%씩 오른 것은 아닙니다.  
        CAGR은 복리 효과를 고려해서 “매년 평균적으로 몇 % 성장한 셈인가?”를 보여줍니다.

        ## 10. 변동성 Volatility
        주가가 얼마나 심하게 흔들리는지를 나타냅니다.

        변동성이 크다는 것은 가격이 크게 오르내린다는 뜻입니다.  
        수익 기회가 클 수도 있지만, 손실 위험도 클 수 있습니다.

        이 앱에서는 일별 수익률의 표준편차를 이용해 연환산 변동성을 계산합니다.

        ## 11. 최대 낙폭 MDD
        Maximum Drawdown의 약자입니다.  
        고점 대비 가장 크게 떨어진 비율을 의미합니다.

        예를 들어 100,000원까지 올랐던 주식이 70,000원까지 떨어졌다면 최대 낙폭은 -30%입니다.

        MDD는 투자자가 경험할 수 있었던 가장 큰 심리적 고통을 보여주는 지표라고도 볼 수 있습니다.

        ## 12. 정규화 비교
        삼성전자와 애플처럼 가격 단위가 다른 주식을 단순 가격으로 비교하면 어렵습니다.

        그래서 시작일 가격을 모두 100으로 맞춘 뒤 비교합니다.  
        이렇게 하면 어느 종목이 더 많이 올랐는지 쉽게 비교할 수 있습니다.

        ## 13. 캔들 차트
        캔들 차트는 하루의 시가, 고가, 저가, 종가를 한 번에 보여주는 차트입니다.

        - 몸통: 시가와 종가 사이의 범위
        - 위 꼬리: 고가까지 올라간 흔적
        - 아래 꼬리: 저가까지 내려간 흔적

        주식 가격이 하루 동안 어떻게 움직였는지 직관적으로 볼 수 있습니다.

        ## 14. ETF
        Exchange Traded Fund의 약자입니다.  
        여러 주식이나 자산을 한 바구니에 담아 거래하는 상품입니다.

        예를 들어 S&P500 ETF는 미국 대표 기업 500개에 분산 투자하는 효과를 줍니다.

        ## 15. 티커 Ticker
        주식을 구분하기 위한 코드입니다.

        예를 들어:

        - 삼성전자: 005930.KS
        - SK하이닉스: 000660.KS
        - Apple: AAPL
        - Microsoft: MSFT
        - S&P500 지수: ^GSPC

        yfinance에서 한국 주식은 보통 `.KS` 또는 `.KQ`를 붙여야 합니다.
        """
    )
