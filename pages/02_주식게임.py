import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import random
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, timedelta

st.set_page_config(
    page_title="주식 탐정단: 주가 예측 게임",
    page_icon="🕵️‍♂️",
    layout="wide"
)

# -------------------------------------------------
# 기본 티커 목록
# -------------------------------------------------

DEFAULT_TICKERS = {
    "한국 주식": {
        "삼성전자": "005930.KS",
        "SK하이닉스": "000660.KS",
        "현대차": "005380.KS",
        "NAVER": "035420.KS",
        "카카오": "035720.KS",
        "셀트리온": "068270.KS",
        "LG에너지솔루션": "373220.KS",
    },
    "미국 주식": {
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
        "금 ETF": "GLD",
        "미국 장기채 ETF": "TLT",
    },
    "지수": {
        "KOSPI": "^KS11",
        "KOSDAQ": "^KQ11",
        "S&P500": "^GSPC",
        "NASDAQ": "^IXIC",
        "Dow Jones": "^DJI",
    }
}

# -------------------------------------------------
# 데이터 함수
# -------------------------------------------------

@st.cache_data(ttl=3600)
def load_data(ticker, start_date, end_date):
    df = yf.download(
        ticker,
        start=start_date,
        end=end_date,
        auto_adjust=False,
        progress=False
    )

    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna()
    return df


def add_indicators(df):
    df = df.copy()
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()
    df["Daily Return"] = df["Close"].pct_change()
    df["Volatility20"] = df["Daily Return"].rolling(20).std() * np.sqrt(252)
    return df


def make_game_round(df, visible_days=60, hidden_days=10):
    """
    전체 데이터 중 임의의 구간을 뽑는다.
    앞 visible_days일은 학생에게 보여주고,
    뒤 hidden_days일은 예측 후 공개한다.
    """
    min_needed = visible_days + hidden_days + 80

    if len(df) < min_needed:
        return None

    start_idx = random.randint(80, len(df) - visible_days - hidden_days - 1)
    visible_start = start_idx
    visible_end = start_idx + visible_days
    hidden_end = visible_end + hidden_days

    visible_df = df.iloc[visible_start:visible_end].copy()
    hidden_df = df.iloc[visible_end:hidden_end].copy()

    return visible_df, hidden_df


def judge_result(visible_df, hidden_df):
    start_price = visible_df["Close"].iloc[-1]
    end_price = hidden_df["Close"].iloc[-1]

    return_rate = end_price / start_price - 1

    if return_rate >= 0.03:
        actual = "상승"
    elif return_rate <= -0.03:
        actual = "하락"
    else:
        actual = "횡보"

    return actual, return_rate, start_price, end_price


def calculate_score(prediction, actual, confidence, return_rate, invest_ratio):
    """
    prediction: 학생 예측
    actual: 실제 결과
    confidence: 자신감 1~5
    invest_ratio: 투자 비중 0~100
    """

    correct = prediction == actual

    base_score = 0

    if correct:
        base_score += 60
    else:
        base_score -= 20

    # 자신감 보정
    if correct:
        base_score += confidence * 5
    else:
        base_score -= confidence * 5

    # 투자 비중 보정
    risk_factor = invest_ratio / 100

    if prediction == "상승":
        simulated_profit = return_rate * risk_factor
    elif prediction == "하락":
        simulated_profit = -return_rate * risk_factor
    else:
        simulated_profit = -abs(return_rate) * risk_factor * 0.5

    profit_score = simulated_profit * 100

    final_score = base_score + profit_score
    final_score = round(final_score, 1)

    return correct, simulated_profit, final_score


def get_feedback(prediction, actual, confidence, invest_ratio, return_rate, visible_df):
    recent_close = visible_df["Close"].iloc[-1]
    ma20 = visible_df["MA20"].iloc[-1]
    ma60 = visible_df["MA60"].iloc[-1]
    recent_volume = visible_df["Volume"].iloc[-5:].mean()
    past_volume = visible_df["Volume"].iloc[-20:].mean()

    comments = []

    if prediction == actual:
        comments.append("예측 방향이 실제 결과와 일치했습니다. 차트의 흐름을 잘 읽었습니다.")
    else:
        comments.append("예측 방향이 실제 결과와 달랐습니다. 주식 시장은 항상 불확실하다는 점을 보여줍니다.")

    if recent_close > ma20 > ma60:
        comments.append("최근 종가가 20일선과 60일선 위에 있어 상승 추세로 해석할 수 있는 구간이었습니다.")
    elif recent_close < ma20 < ma60:
        comments.append("최근 종가가 20일선과 60일선 아래에 있어 하락 추세로 해석할 수 있는 구간이었습니다.")
    else:
        comments.append("이동평균선이 뚜렷하게 정렬되지 않아 방향 판단이 어려운 구간이었습니다.")

    if recent_volume > past_volume * 1.2:
        comments.append("최근 거래량이 평소보다 많았습니다. 시장의 관심이 커진 구간일 가능성이 있습니다.")
    elif recent_volume < past_volume * 0.8:
        comments.append("최근 거래량이 줄어든 편이었습니다. 시장의 관심이 약해졌을 가능성이 있습니다.")
    else:
        comments.append("최근 거래량은 평소와 비슷한 수준이었습니다.")

    if confidence >= 4 and prediction != actual:
        comments.append("자신감이 높았지만 결과가 달랐습니다. 예측에서는 확신보다 근거와 위험 관리가 중요합니다.")

    if invest_ratio >= 70:
        comments.append("투자 비중이 높았습니다. 맞히면 수익이 커지지만, 틀리면 손실도 커집니다.")
    elif invest_ratio <= 30:
        comments.append("투자 비중을 낮게 잡았습니다. 보수적인 위험 관리 전략으로 볼 수 있습니다.")

    if abs(return_rate) < 0.03:
        comments.append("실제 주가는 큰 방향성 없이 움직였습니다. 이럴 때는 상승·하락보다 횡보 판단이 중요합니다.")

    return comments


def plot_visible_chart(visible_df, title):
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.08,
        subplot_titles=("학생에게 공개된 주가 흐름", "거래량")
    )

    fig.add_trace(
        go.Candlestick(
            x=visible_df.index,
            open=visible_df["Open"],
            high=visible_df["High"],
            low=visible_df["Low"],
            close=visible_df["Close"],
            name="가격"
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=visible_df.index,
            y=visible_df["MA5"],
            mode="lines",
            name="5일 이동평균선"
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=visible_df.index,
            y=visible_df["MA20"],
            mode="lines",
            name="20일 이동평균선"
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=visible_df.index,
            y=visible_df["MA60"],
            mode="lines",
            name="60일 이동평균선"
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Bar(
            x=visible_df.index,
            y=visible_df["Volume"],
            name="거래량"
        ),
        row=2,
        col=1
    )

    fig.update_layout(
        title=title,
        height=720,
        hovermode="x unified",
        xaxis_rangeslider_visible=False
    )

    return fig


def plot_reveal_chart(visible_df, hidden_df, title):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=visible_df.index,
            y=visible_df["Close"],
            mode="lines",
            name="공개 구간"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=hidden_df.index,
            y=hidden_df["Close"],
            mode="lines+markers",
            name="실제 결과 공개 구간"
        )
    )

    fig.add_vline(
        x=visible_df.index[-1],
        line_dash="dash",
        annotation_text="예측 시점",
        annotation_position="top"
    )

    fig.update_layout(
        title=title,
        xaxis_title="날짜",
        yaxis_title="종가",
        height=600,
        hovermode="x unified"
    )

    return fig


# -------------------------------------------------
# 세션 상태 초기화
# -------------------------------------------------

if "round_ready" not in st.session_state:
    st.session_state.round_ready = False

if "score_history" not in st.session_state:
    st.session_state.score_history = []

if "total_score" not in st.session_state:
    st.session_state.total_score = 0

if "round_count" not in st.session_state:
    st.session_state.round_count = 0


# -------------------------------------------------
# 제목
# -------------------------------------------------

st.title("🕵️‍♂️ 주식 탐정단: 다음 주가는 어디로?")
st.caption("차트를 보고 다음 10거래일의 주가 흐름을 예측하는 교육용 주식 데이터 게임입니다.")

st.warning(
    "이 앱은 투자 교육용 게임입니다. 실제 투자 추천이 아닙니다. "
    "주식 시장은 예측이 어렵고 손실 위험이 있습니다."
)

# -------------------------------------------------
# 사이드바
# -------------------------------------------------

st.sidebar.header("🎮 게임 설정")

market = st.sidebar.selectbox(
    "시장 선택",
    list(DEFAULT_TICKERS.keys())
)

stock_name = st.sidebar.selectbox(
    "종목 선택",
    list(DEFAULT_TICKERS[market].keys())
)

ticker = DEFAULT_TICKERS[market][stock_name]

custom_ticker = st.sidebar.text_input(
    "직접 티커 입력",
    placeholder="예: AAPL, MSFT, 005930.KS"
)

if custom_ticker.strip():
    ticker = custom_ticker.strip().upper()
    stock_name = ticker

difficulty = st.sidebar.selectbox(
    "난이도",
    ["쉬움", "보통", "어려움"],
    index=1
)

if difficulty == "쉬움":
    visible_days = 90
    hidden_days = 10
elif difficulty == "보통":
    visible_days = 60
    hidden_days = 10
else:
    visible_days = 40
    hidden_days = 10

st.sidebar.markdown("---")

if st.sidebar.button("🔄 점수 초기화"):
    st.session_state.score_history = []
    st.session_state.total_score = 0
    st.session_state.round_count = 0
    st.session_state.round_ready = False
    st.rerun()


# -------------------------------------------------
# 데이터 불러오기
# -------------------------------------------------

start_date = date.today() - timedelta(days=365 * 6)
end_date = date.today() + timedelta(days=1)

df = load_data(ticker, start_date, end_date)

if df.empty:
    st.error("데이터를 불러오지 못했습니다. 티커를 다시 확인해주세요.")
    st.stop()

df = add_indicators(df)
df = df.dropna()

# -------------------------------------------------
# 게임 소개
# -------------------------------------------------

with st.expander("🎯 게임 방법 보기", expanded=True):
    st.markdown(
        """
        ## 게임 규칙

        1. 앱이 과거의 임의 구간을 선택합니다.
        2. 학생에게는 앞부분 차트만 공개됩니다.
        3. 학생은 다음 10거래일 동안 주가가 **상승 / 하락 / 횡보** 중 어디로 갈지 예측합니다.
        4. 예측의 자신감과 투자 비중도 함께 선택합니다.
        5. 결과를 공개하면 실제 주가 흐름과 점수가 나타납니다.

        ## 교육 포인트

        - 주가는 무조건 맞힐 수 있는 대상이 아니라는 점을 이해합니다.
        - 차트, 이동평균선, 거래량을 근거로 예측하는 연습을 합니다.
        - 높은 수익률에는 높은 위험이 함께 따라올 수 있음을 배웁니다.
        - 투자에서 중요한 것은 예측뿐 아니라 위험 관리라는 점을 배웁니다.
        """
    )


# -------------------------------------------------
# 새 라운드 생성
# -------------------------------------------------

col_a, col_b, col_c = st.columns([1, 1, 2])

with col_a:
    new_round = st.button("🎲 새 문제 뽑기", use_container_width=True)

with col_b:
    reveal = st.button("📢 결과 공개", use_container_width=True)

if new_round:
    game_round = make_game_round(df, visible_days=visible_days, hidden_days=hidden_days)

    if game_round is None:
        st.error("게임을 만들기에 데이터가 충분하지 않습니다.")
        st.stop()

    visible_df, hidden_df = game_round

    st.session_state.visible_df = visible_df
    st.session_state.hidden_df = hidden_df
    st.session_state.round_ready = True
    st.session_state.revealed = False
    st.rerun()


if not st.session_state.round_ready:
    st.info("먼저 왼쪽 또는 위쪽의 **새 문제 뽑기** 버튼을 눌러주세요.")
    st.stop()


visible_df = st.session_state.visible_df
hidden_df = st.session_state.hidden_df

# -------------------------------------------------
# 현재 점수판
# -------------------------------------------------

st.markdown("## 🏆 현재 점수판")

score_col1, score_col2, score_col3 = st.columns(3)

score_col1.metric("누적 점수", f"{st.session_state.total_score:.1f}점")
score_col2.metric("진행 라운드", f"{st.session_state.round_count}회")

if st.session_state.round_count > 0:
    avg_score = st.session_state.total_score / st.session_state.round_count
else:
    avg_score = 0

score_col3.metric("평균 점수", f"{avg_score:.1f}점")

# -------------------------------------------------
# 공개 차트
# -------------------------------------------------

st.markdown("## 1단계. 차트 관찰하기")

st.plotly_chart(
    plot_visible_chart(
        visible_df,
        f"{stock_name} ({ticker}) - 예측 전 공개 차트"
    ),
    use_container_width=True
)

# -------------------------------------------------
# 예측 입력
# -------------------------------------------------

st.markdown("## 2단계. 주가 예측하기")

col1, col2, col3 = st.columns(3)

with col1:
    prediction = st.radio(
        "다음 10거래일 뒤 주가는?",
        ["상승", "하락", "횡보"],
        horizontal=True
    )

with col2:
    confidence = st.slider(
        "예측 자신감",
        min_value=1,
        max_value=5,
        value=3,
        help="1은 거의 모르겠다, 5는 매우 자신 있다는 뜻입니다."
    )

with col3:
    invest_ratio = st.slider(
        "가상의 투자 비중",
        min_value=0,
        max_value=100,
        value=50,
        step=10,
        help="내 가상 자산 중 몇 %를 투자할지 정합니다."
    )

reason = st.multiselect(
    "예측 근거를 선택해보세요.",
    [
        "최근 주가가 상승 추세로 보인다",
        "최근 주가가 하락 추세로 보인다",
        "이동평균선이 상승 방향으로 정렬되어 있다",
        "이동평균선이 하락 방향으로 정렬되어 있다",
        "거래량이 증가했다",
        "거래량이 감소했다",
        "가격 변동성이 크다",
        "뚜렷한 방향이 없어 보인다",
        "뉴스나 시장 분위기를 고려했다",
        "솔직히 감으로 골랐다"
    ]
)

student_memo = st.text_area(
    "나의 예측 메모",
    placeholder="예: 20일 이동평균선 위에서 가격이 움직이고 있고, 최근 거래량도 늘어서 상승을 예상했다."
)

# -------------------------------------------------
# 결과 공개
# -------------------------------------------------

if reveal:
    actual, return_rate, start_price, end_price = judge_result(visible_df, hidden_df)

    correct, simulated_profit, final_score = calculate_score(
        prediction,
        actual,
        confidence,
        return_rate,
        invest_ratio
    )

    st.session_state.total_score += final_score
    st.session_state.round_count += 1

    st.session_state.score_history.append({
        "라운드": st.session_state.round_count,
        "종목": ticker,
        "예측": prediction,
        "실제": actual,
        "실제 수익률": return_rate,
        "투자 비중": invest_ratio,
        "자신감": confidence,
        "점수": final_score
    })

    st.markdown("## 3단계. 실제 결과 공개")

    result_col1, result_col2, result_col3, result_col4 = st.columns(4)

    result_col1.metric("내 예측", prediction)
    result_col2.metric("실제 결과", actual)
    result_col3.metric("10거래일 수익률", f"{return_rate * 100:.2f}%")
    result_col4.metric("이번 라운드 점수", f"{final_score:.1f}점")

    if correct:
        st.success("정답입니다. 주식 탐정의 촉이 좋았습니다!")
    else:
        st.error("예측이 빗나갔습니다. 하지만 이것이 바로 시장의 불확실성입니다.")

    st.plotly_chart(
        plot_reveal_chart(
            visible_df,
            hidden_df,
            f"{stock_name} ({ticker}) - 실제 결과 공개"
        ),
        use_container_width=True
    )

    st.markdown("### 💰 가상 투자 결과")

    if simulated_profit >= 0:
        st.success(f"가상 투자 수익률: {simulated_profit * 100:.2f}%")
    else:
        st.error(f"가상 투자 수익률: {simulated_profit * 100:.2f}%")

    st.markdown("### 🧠 AI 피드백")

    feedback_list = get_feedback(
        prediction,
        actual,
        confidence,
        invest_ratio,
        return_rate,
        visible_df
    )

    for item in feedback_list:
        st.write(f"- {item}")

    if reason:
        st.markdown("### ✍️ 내가 선택한 예측 근거")
        for r in reason:
            st.write(f"- {r}")

    if student_memo.strip():
        st.markdown("### 📝 나의 예측 메모")
        st.write(student_memo)

# -------------------------------------------------
# 기록표
# -------------------------------------------------

if st.session_state.score_history:
    st.markdown("## 📜 나의 예측 기록")

    history_df = pd.DataFrame(st.session_state.score_history)

    display_history = history_df.copy()
    display_history["실제 수익률"] = display_history["실제 수익률"].map(lambda x: f"{x * 100:.2f}%")
    display_history["투자 비중"] = display_history["투자 비중"].map(lambda x: f"{x}%")
    display_history["점수"] = display_history["점수"].map(lambda x: f"{x:.1f}")

    st.dataframe(display_history, use_container_width=True)

    fig_score = go.Figure()

    fig_score.add_trace(
        go.Scatter(
            x=history_df["라운드"],
            y=history_df["점수"],
            mode="lines+markers",
            name="라운드별 점수"
        )
    )

    fig_score.update_layout(
        title="라운드별 점수 변화",
        xaxis_title="라운드",
        yaxis_title="점수",
        height=400
    )

    st.plotly_chart(fig_score, use_container_width=True)

# -------------------------------------------------
# 교육용 설명
# -------------------------------------------------

st.markdown("---")
st.markdown("## 📚 오늘 배운 주식 개념")

term_tab1, term_tab2, term_tab3, term_tab4 = st.tabs(
    ["추세", "이동평균선", "거래량", "위험 관리"]
)

with term_tab1:
    st.markdown(
        """
        ### 추세란?

        추세는 주가가 전체적으로 움직이는 방향입니다.

        - 계속 올라가는 흐름이면 상승 추세
        - 계속 내려가는 흐름이면 하락 추세
        - 크게 방향이 없으면 횡보

        하지만 추세가 보인다고 해서 반드시 그 방향으로 계속 간다는 뜻은 아닙니다.  
        주식 시장은 언제든 예상과 다르게 움직일 수 있습니다.
        """
    )

with term_tab2:
    st.markdown(
        """
        ### 이동평균선이란?

        이동평균선은 일정 기간 동안의 평균 가격을 선으로 나타낸 것입니다.

        예를 들어 20일 이동평균선은 최근 20거래일의 평균 가격입니다.

        이동평균선은 주가의 흐름을 부드럽게 보여줍니다.

        - 주가가 이동평균선 위에 있으면 비교적 강한 흐름으로 볼 수 있습니다.
        - 주가가 이동평균선 아래에 있으면 비교적 약한 흐름으로 볼 수 있습니다.
        - 단기선이 장기선 위에 있으면 상승 흐름으로 해석하기도 합니다.
        - 단기선이 장기선 아래에 있으면 하락 흐름으로 해석하기도 합니다.

        단, 이동평균선은 미래를 맞히는 마법 공식이 아닙니다.  
        과거 가격을 평균낸 것이기 때문에 참고 자료로만 사용해야 합니다.
        """
    )

with term_tab3:
    st.markdown(
        """
        ### 거래량이란?

        거래량은 일정 기간 동안 사고팔린 주식 수입니다.

        거래량이 많다는 것은 그 주식에 관심을 가진 사람이 많다는 뜻일 수 있습니다.

        예를 들어 주가가 오르면서 거래량도 늘어나면 많은 사람들이 매수에 참여했다고 볼 수 있습니다.  
        반대로 주가가 떨어지면서 거래량이 늘어나면 많은 사람들이 매도에 참여했다고 볼 수도 있습니다.

        하지만 거래량도 혼자 보면 안 됩니다.  
        가격 흐름, 이동평균선, 시장 상황과 함께 봐야 합니다.
        """
    )

with term_tab4:
    st.markdown(
        """
        ### 위험 관리란?

        주식 투자에서 중요한 것은 예측을 한 번 맞히는 것이 아닙니다.  
        틀렸을 때 손실을 얼마나 줄일 수 있는지가 매우 중요합니다.

        이 게임에서 투자 비중을 정하게 한 이유도 바로 이것입니다.

        - 투자 비중이 크면 맞혔을 때 점수가 크게 올라갑니다.
        - 하지만 틀렸을 때 점수도 크게 떨어집니다.
        - 투자 비중이 작으면 수익은 작지만 손실도 줄일 수 있습니다.

        실제 투자에서도 모든 돈을 한 종목에 몰아넣는 것은 매우 위험합니다.  
        분산 투자와 위험 관리는 장기적으로 매우 중요한 태도입니다.
        """
    )
