import html
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf


# =========================================================
# 기본 설정
# =========================================================

st.set_page_config(
    page_title="주식 탐정단 2.0",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    "ETF · 지수": {
        "S&P500 ETF": "SPY",
        "NASDAQ100 ETF": "QQQ",
        "미국 전체시장 ETF": "VTI",
        "금 ETF": "GLD",
        "KOSPI": "^KS11",
        "KOSDAQ": "^KQ11",
        "S&P500 지수": "^GSPC",
        "NASDAQ 지수": "^IXIC",
    },
}

DIFFICULTIES = {
    "입문 모드": {
        "visible_days": 90,
        "hidden_days": 10,
        "threshold": 0.02,
        "description": "차트를 넉넉히 보여주고 힌트 카드를 제공합니다.",
        "show_hints": True,
        "chart_mode": "line",
    },
    "탐정 모드": {
        "visible_days": 65,
        "hidden_days": 10,
        "threshold": 0.025,
        "description": "정보량과 난이도가 균형 잡힌 기본 모드입니다.",
        "show_hints": True,
        "chart_mode": "candle",
    },
    "퀀트 모드": {
        "visible_days": 45,
        "hidden_days": 10,
        "threshold": 0.03,
        "description": "힌트가 줄고, 짧은 차트에서 판단해야 합니다.",
        "show_hints": False,
        "chart_mode": "candle",
    },
}

EVIDENCE_OPTIONS = [
    "최근 가격이 상승 흐름이다",
    "최근 가격이 하락 흐름이다",
    "단기 평균선이 장기 평균선 위에 있다",
    "단기 평균선이 장기 평균선 아래에 있다",
    "거래량이 평소보다 늘었다",
    "거래량이 평소보다 줄었다",
    "최근 변동성이 커서 조심해야 한다",
    "방향성이 약해 횡보 가능성이 있다",
    "짧은 기간에 너무 많이 올라 조정 가능성이 있다",
    "짧은 기간에 많이 내려 반등 가능성이 있다",
]


# =========================================================
# CSS: 과한 장식보다 카드형 게임 UI 중심
# =========================================================

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 3rem;
        max-width: 1320px;
    }
    .hero {
        border-radius: 28px;
        padding: 28px 30px;
        margin-bottom: 18px;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 46%, #0f766e 100%);
        color: white;
        box-shadow: 0 20px 55px rgba(15, 23, 42, 0.20);
    }
    .hero h1 {
        margin: 0;
        font-size: 2.25rem;
        line-height: 1.15;
        letter-spacing: -0.04em;
    }
    .hero p {
        margin-top: 10px;
        margin-bottom: 0;
        font-size: 1.05rem;
        color: rgba(255, 255, 255, 0.86);
    }
    .pill-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 18px;
    }
    .pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 12px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.13);
        border: 1px solid rgba(255, 255, 255, 0.20);
        color: white;
        font-size: 0.9rem;
        backdrop-filter: blur(6px);
    }
    .ux-card {
        border-radius: 22px;
        padding: 18px 18px;
        background: #ffffff;
        border: 1px solid #e5e7eb;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
        height: 100%;
    }
    .ux-card-soft {
        border-radius: 22px;
        padding: 18px 18px;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e5e7eb;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
        height: 100%;
    }
    .small-label {
        color: #64748b;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .big-value {
        color: #0f172a;
        font-size: 1.45rem;
        font-weight: 850;
        letter-spacing: -0.03em;
        margin-bottom: 6px;
    }
    .sub-note {
        color: #475569;
        font-size: 0.92rem;
        line-height: 1.42;
    }
    .step-title {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 7px 12px;
        margin-top: 12px;
        margin-bottom: 10px;
        border-radius: 999px;
        background: #ecfeff;
        color: #155e75;
        font-size: 0.93rem;
        font-weight: 800;
        border: 1px solid #cffafe;
    }
    .result-good {
        border-radius: 26px;
        padding: 22px 24px;
        background: linear-gradient(135deg, #ecfdf5 0%, #ffffff 100%);
        border: 1px solid #bbf7d0;
    }
    .result-bad {
        border-radius: 26px;
        padding: 22px 24px;
        background: linear-gradient(135deg, #fff7ed 0%, #ffffff 100%);
        border: 1px solid #fed7aa;
    }
    .caption-box {
        border-left: 4px solid #14b8a6;
        background: #f8fafc;
        border-radius: 14px;
        padding: 12px 14px;
        color: #334155;
        line-height: 1.55;
    }
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 14px 16px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
    }
    section[data-testid="stSidebar"] {
        background: #f8fafc;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 유틸 함수
# =========================================================

def safe_text(value):
    return html.escape(str(value))


def percent_text(value, digits=2):
    if value is None or pd.isna(value):
        return "-"
    return f"{value * 100:.{digits}f}%"


def money_text(value):
    if value is None or pd.isna(value):
        return "-"
    return f"{value:,.0f}"


def render_card(label, value, note, emoji=""):
    st.markdown(
        f"""
        <div class="ux-card-soft">
            <div class="small-label">{safe_text(emoji)} {safe_text(label)}</div>
            <div class="big-value">{safe_text(value)}</div>
            <div class="sub-note">{safe_text(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def load_price_data(ticker, start_date, end_date):
    """yfinance에서 일봉 데이터를 불러온다."""
    df = yf.download(
        tickers=ticker,
        start=start_date,
        end=end_date,
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if df is None or df.empty:
        return pd.DataFrame()

    # yfinance 버전/옵션에 따라 MultiIndex로 오는 경우를 단일 컬럼으로 정리
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        return pd.DataFrame()

    df = df[required_cols].copy()
    for col in required_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Volume"] = df["Volume"].fillna(0)
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df.index = pd.to_datetime(df.index)
    return df


def add_indicators(df):
    df = df.copy()
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()
    df["Daily Return"] = df["Close"].pct_change()
    df["Return5"] = df["Close"].pct_change(5)
    df["Return20"] = df["Close"].pct_change(20)
    df["Volatility20"] = df["Daily Return"].rolling(20).std() * np.sqrt(252)
    return df.dropna()


def make_round(df, ticker, stock_name, difficulty_name, blind_mode):
    settings = DIFFICULTIES[difficulty_name]
    visible_days = settings["visible_days"]
    hidden_days = settings["hidden_days"]

    min_length = visible_days + hidden_days + 10
    if len(df) < min_length:
        return None

    max_start = len(df) - visible_days - hidden_days - 1
    start_idx = random.randint(0, max_start)
    visible_df = df.iloc[start_idx : start_idx + visible_days].copy()
    hidden_df = df.iloc[start_idx + visible_days : start_idx + visible_days + hidden_days].copy()

    return {
        "round_id": random.randint(1000, 9999),
        "ticker": ticker,
        "stock_name": stock_name,
        "difficulty": difficulty_name,
        "blind_mode": blind_mode,
        "visible_df": visible_df,
        "hidden_df": hidden_df,
        "visible_days": visible_days,
        "hidden_days": hidden_days,
        "threshold": settings["threshold"],
        "show_hints": settings["show_hints"],
        "chart_mode": settings["chart_mode"],
    }


def normalize_price_frame(df, base_price):
    out = df.copy()
    price_cols = ["Open", "High", "Low", "Close", "MA5", "MA20", "MA60"]
    for col in price_cols:
        if col in out.columns:
            out[col] = out[col] / base_price * 100
    return out


def create_chart_frames(visible_df, hidden_df=None, blind_mode=True):
    base_price = visible_df["Close"].iloc[0]

    if blind_mode:
        v = normalize_price_frame(visible_df, base_price)
        v["X"] = list(range(1, len(v) + 1))
        if hidden_df is not None:
            h = normalize_price_frame(hidden_df, base_price)
            h["X"] = list(range(len(v) + 1, len(v) + len(h) + 1))
            return v, h, "게임일", "시작일 = 100"
        return v, None, "게임일", "시작일 = 100"

    v = visible_df.copy()
    v["X"] = v.index
    if hidden_df is not None:
        h = hidden_df.copy()
        h["X"] = h.index
        return v, h, "날짜", "가격"
    return v, None, "날짜", "가격"


def analyze_visible_signals(visible_df):
    last = visible_df.iloc[-1]
    close = last["Close"]
    ma5 = last["MA5"]
    ma20 = last["MA20"]
    ma60 = last["MA60"]
    return5 = last["Return5"]
    return20 = last["Return20"]
    vol20 = last["Volatility20"]

    recent_volume = visible_df["Volume"].tail(5).mean()
    base_volume = visible_df["Volume"].tail(25).mean()
    volume_ratio = recent_volume / base_volume if base_volume and base_volume > 0 else np.nan

    if close > ma20 > ma60:
        trend_title = "상승 단서"
        trend_note = "종가가 20일·60일 평균선 위쪽에 있습니다."
        trend_emoji = "📈"
    elif close < ma20 < ma60:
        trend_title = "하락 단서"
        trend_note = "종가가 20일·60일 평균선 아래쪽에 있습니다."
        trend_emoji = "📉"
    else:
        trend_title = "혼합 신호"
        trend_note = "평균선 배열이 깔끔하지 않아 판단이 어렵습니다."
        trend_emoji = "🧩"

    if pd.isna(volume_ratio):
        volume_title = "거래량 정보 약함"
        volume_note = "지수나 일부 종목은 거래량 정보가 제한적일 수 있습니다."
        volume_emoji = "🕯️"
    elif volume_ratio >= 1.25:
        volume_title = "관심 증가"
        volume_note = "최근 5일 거래량이 평소보다 많습니다."
        volume_emoji = "🔥"
    elif volume_ratio <= 0.75:
        volume_title = "관심 감소"
        volume_note = "최근 5일 거래량이 평소보다 적습니다."
        volume_emoji = "💤"
    else:
        volume_title = "거래량 보통"
        volume_note = "최근 거래량이 평소와 크게 다르지 않습니다."
        volume_emoji = "⚖️"

    if vol20 >= 0.45:
        risk_title = "고위험 구간"
        risk_note = "최근 가격 흔들림이 큽니다. 투자 비중을 조심해야 합니다."
        risk_emoji = "⚠️"
    elif vol20 >= 0.25:
        risk_title = "중간 변동성"
        risk_note = "가격 변동이 어느 정도 있는 구간입니다."
        risk_emoji = "🌊"
    else:
        risk_title = "낮은 변동성"
        risk_note = "최근 가격 흔들림이 비교적 작은 편입니다."
        risk_emoji = "🧘"

    if return5 >= 0.04:
        momentum_title = "단기 강세"
        momentum_note = "최근 5거래일 수익률이 높습니다. 과열 가능성도 함께 봐야 합니다."
        momentum_emoji = "🚀"
    elif return5 <= -0.04:
        momentum_title = "단기 약세"
        momentum_note = "최근 5거래일 하락 폭이 큽니다. 추가 하락과 반등을 모두 생각해야 합니다."
        momentum_emoji = "🧊"
    else:
        momentum_title = "단기 방향 약함"
        momentum_note = "최근 5거래일 기준으로 큰 방향성이 약합니다."
        momentum_emoji = "➡️"

    return {
        "trend": (trend_emoji, trend_title, trend_note),
        "volume": (volume_emoji, volume_title, volume_note),
        "risk": (risk_emoji, risk_title, risk_note),
        "momentum": (momentum_emoji, momentum_title, momentum_note),
        "raw": {
            "close": close,
            "ma5": ma5,
            "ma20": ma20,
            "ma60": ma60,
            "return5": return5,
            "return20": return20,
            "vol20": vol20,
            "volume_ratio": volume_ratio,
        },
    }


def judge_actual(visible_df, hidden_df, threshold):
    start_price = visible_df["Close"].iloc[-1]
    end_price = hidden_df["Close"].iloc[-1]
    return_rate = end_price / start_price - 1

    if return_rate >= threshold:
        actual = "상승"
    elif return_rate <= -threshold:
        actual = "하락"
    else:
        actual = "횡보"

    return actual, return_rate, start_price, end_price


def prediction_to_plain(prediction_label):
    if "상승" in prediction_label:
        return "상승"
    if "하락" in prediction_label:
        return "하락"
    return "횡보"


def simulate_coin_result(prediction, return_rate, stake_coins, threshold):
    if prediction == "상승":
        game_return = return_rate
    elif prediction == "하락":
        game_return = -return_rate
    else:
        # 횡보 예측은 실제 변동폭이 작을수록 보상, 클수록 손실
        game_return = threshold - abs(return_rate)

    coin_delta = stake_coins * game_return * 4
    return round(coin_delta, 1), game_return


def calculate_score(prediction, actual, confidence, stake_pct, evidence_count, memo, coin_delta):
    correct = prediction == actual

    if correct:
        score = 70
    else:
        score = 15

    # 근거를 고른 학생에게 과정 점수를 준다.
    score += min(evidence_count, 3) * 5

    if memo.strip():
        score += 5

    # 위험 관리 점수
    if not correct and stake_pct <= 40:
        score += 10
    elif not correct and stake_pct >= 80:
        score -= 10

    if not correct and confidence >= 5:
        score -= 10
    elif correct and confidence >= 4:
        score += 5

    # 가상 코인 결과도 조금 반영한다.
    score += max(min(coin_delta / 10, 15), -15)

    return round(max(score, 0), 1), correct


def build_feedback(prediction, actual, return_rate, threshold, confidence, stake_pct, signals):
    feedback = []

    feedback.append(
        f"실제 10거래일 수익률은 {percent_text(return_rate)}입니다. "
        f"이 게임에서는 ±{threshold * 100:.1f}% 안쪽이면 횡보로 판정합니다."
    )

    if prediction == actual:
        feedback.append("예측 방향이 실제 결과와 일치했습니다. 다만 한 번의 정답이 실력을 보장하지는 않으므로 근거를 복기해야 합니다.")
    else:
        feedback.append("예측이 빗나갔습니다. 주식 데이터는 판단을 돕지만 미래를 확정하지는 못한다는 점을 보여줍니다.")

    raw = signals["raw"]
    if raw["close"] > raw["ma20"] > raw["ma60"]:
        feedback.append("관찰 구간 마지막 날에는 종가가 20일선과 60일선 위에 있어 상승 추세 단서가 있었습니다.")
    elif raw["close"] < raw["ma20"] < raw["ma60"]:
        feedback.append("관찰 구간 마지막 날에는 종가가 20일선과 60일선 아래에 있어 하락 추세 단서가 있었습니다.")
    else:
        feedback.append("관찰 구간 마지막 날의 이동평균선 배열은 뚜렷하지 않아 상승·하락 판단이 어려운 장면이었습니다.")

    if confidence >= 4 and prediction != actual:
        feedback.append("자신감은 높았지만 결과가 달랐습니다. 데이터 분석에서는 '확신'보다 '확률적으로 생각하기'가 중요합니다.")

    if stake_pct >= 80:
        feedback.append("투자 비중을 크게 잡았습니다. 맞히면 점수가 커지지만, 틀리면 손실도 커지는 선택입니다.")
    elif stake_pct <= 30:
        feedback.append("투자 비중을 낮게 잡았습니다. 수익 기회는 줄지만 손실을 관리하는 보수적 선택입니다.")

    return feedback


def plot_mystery_chart(game_round):
    visible_df = game_round["visible_df"]
    blind_mode = game_round["blind_mode"]
    chart_mode = game_round["chart_mode"]
    v, _, x_title, y_title = create_chart_frames(visible_df, blind_mode=blind_mode)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.72, 0.28],
        subplot_titles=("관찰 가능한 가격 흐름", "거래량"),
    )

    if chart_mode == "line":
        fig.add_trace(
            go.Scatter(
                x=v["X"],
                y=v["Close"],
                mode="lines",
                name="종가",
                line=dict(width=3),
            ),
            row=1,
            col=1,
        )
    else:
        fig.add_trace(
            go.Candlestick(
                x=v["X"],
                open=v["Open"],
                high=v["High"],
                low=v["Low"],
                close=v["Close"],
                name="시가·고가·저가·종가",
            ),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Scatter(
            x=v["X"],
            y=v["MA20"],
            mode="lines",
            name="20일 평균",
            line=dict(width=2, dash="solid"),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=v["X"],
            y=v["MA60"],
            mode="lines",
            name="60일 평균",
            line=dict(width=2, dash="dot"),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=v["X"],
            y=v["Volume"],
            name="거래량",
            opacity=0.62,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        height=620,
        hovermode="x unified",
        margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(title_text=x_title, row=2, col=1)
    fig.update_yaxes(title_text=y_title, row=1, col=1)
    fig.update_yaxes(title_text="거래량", row=2, col=1)
    return fig


def plot_reveal_chart(game_round):
    visible_df = game_round["visible_df"]
    hidden_df = game_round["hidden_df"]
    blind_mode = game_round["blind_mode"]
    v, h, x_title, y_title = create_chart_frames(visible_df, hidden_df, blind_mode=blind_mode)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=v["X"],
            y=v["Close"],
            mode="lines",
            name="관찰 구간",
            line=dict(width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=h["X"],
            y=h["Close"],
            mode="lines+markers",
            name="공개된 미래 구간",
            line=dict(width=4),
            marker=dict(size=7),
        )
    )

    boundary_x = v["X"].iloc[-1]
    fig.add_vline(
        x=boundary_x,
        line_dash="dash",
        annotation_text="예측 시점",
        annotation_position="top",
    )

    fig.update_layout(
        height=540,
        hovermode="x unified",
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(title_text=x_title)
    fig.update_yaxes(title_text=y_title)
    return fig


def init_state():
    defaults = {
        "game_round": None,
        "config_key": None,
        "revealed": False,
        "last_result": None,
        "history": [],
        "total_score": 0.0,
        "coins": 1000.0,
        "round_no": 0,
        "celebrated_round_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


# =========================================================
# 사이드바: 설정은 최소화
# =========================================================

st.sidebar.title("🎮 게임 설정")

market_group = st.sidebar.selectbox("시장", list(DEFAULT_TICKERS.keys()))
stock_name = st.sidebar.selectbox("종목", list(DEFAULT_TICKERS[market_group].keys()))
ticker = DEFAULT_TICKERS[market_group][stock_name]

custom_ticker = st.sidebar.text_input("직접 티커", placeholder="예: AAPL, 005930.KS")
if custom_ticker.strip():
    ticker = custom_ticker.strip().upper()
    stock_name = ticker

difficulty = st.sidebar.radio(
    "난이도",
    list(DIFFICULTIES.keys()),
    index=1,
)
st.sidebar.caption(DIFFICULTIES[difficulty]["description"])

blind_mode = st.sidebar.toggle(
    "블라인드 모드",
    value=True,
    help="종목명과 실제 가격 대신 비밀 종목, 시작일=100 기준으로 보여줍니다.",
)

st.sidebar.markdown("---")
st.sidebar.metric("보유 코인", f"{st.session_state.coins:,.1f}")
st.sidebar.metric("누적 점수", f"{st.session_state.total_score:,.1f}")
st.sidebar.metric("진행 라운드", f"{st.session_state.round_no}회")

reset_col1, reset_col2 = st.sidebar.columns(2)
with reset_col1:
    reset_game = st.button("초기화", use_container_width=True)
with reset_col2:
    force_new_round = st.button("새 라운드", use_container_width=True, type="primary")

if reset_game:
    st.session_state.game_round = None
    st.session_state.config_key = None
    st.session_state.revealed = False
    st.session_state.last_result = None
    st.session_state.history = []
    st.session_state.total_score = 0.0
    st.session_state.coins = 1000.0
    st.session_state.round_no = 0
    st.session_state.celebrated_round_id = None
    st.rerun()


# =========================================================
# 데이터 로딩 및 라운드 준비
# =========================================================

start_date = date.today() - timedelta(days=365 * 7)
end_date = date.today() + timedelta(days=1)

with st.spinner("주가 데이터를 불러오는 중입니다..."):
    raw_df = load_price_data(ticker, start_date, end_date)

if raw_df.empty:
    st.error("데이터를 불러오지 못했습니다. 티커를 다시 확인해주세요.")
    st.stop()

price_df = add_indicators(raw_df)

if price_df.empty or len(price_df) < 130:
    st.error("게임을 만들기에 데이터가 충분하지 않습니다. 다른 종목이나 지수를 선택해주세요.")
    st.stop()

config_key = f"{ticker}|{difficulty}|{blind_mode}"

if st.session_state.config_key != config_key or st.session_state.game_round is None or force_new_round:
    new_round = make_round(price_df, ticker, stock_name, difficulty, blind_mode)
    if new_round is None:
        st.error("이 종목은 선택한 난이도로 라운드를 만들기에 데이터가 부족합니다.")
        st.stop()
    st.session_state.game_round = new_round
    st.session_state.config_key = config_key
    st.session_state.revealed = False
    st.session_state.last_result = None
    st.rerun()


game_round = st.session_state.game_round
visible_df = game_round["visible_df"]
hidden_df = game_round["hidden_df"]
threshold = game_round["threshold"]
signals = analyze_visible_signals(visible_df)

display_name = "비밀 종목" if game_round["blind_mode"] else f"{game_round['stock_name']} · {game_round['ticker']}"


# =========================================================
# 헤더
# =========================================================

st.markdown(
    f"""
    <div class="hero">
        <h1>🕵️ 주식 탐정단 2.0</h1>
        <p>차트의 앞부분만 보고, 다음 {game_round['hidden_days']}거래일의 방향을 예측하는 데이터 추리 게임</p>
        <div class="pill-row">
            <span class="pill">🎯 미션: 상승 · 횡보 · 하락 예측</span>
            <span class="pill">🧠 근거 선택 필수</span>
            <span class="pill">💰 가상 코인으로 위험 관리</span>
            <span class="pill">🔒 {safe_text('블라인드' if game_round['blind_mode'] else '실명')} 모드</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.warning(
    "교육용 모의 게임입니다. 실제 매수·매도 추천이 아니며, yfinance 데이터는 지연·누락될 수 있습니다."
)


# =========================================================
# 진행 흐름
# =========================================================

step_current = 4 if st.session_state.revealed else 2
st.progress(step_current / 4)

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("라운드", f"#{game_round['round_id']}")
col_m2.metric("대상", display_name)
col_m3.metric("예측 기간", f"{game_round['hidden_days']}거래일")
col_m4.metric("횡보 기준", f"±{threshold * 100:.1f}%")


# =========================================================
# 1단계: 관찰 카드
# =========================================================

st.markdown('<div class="step-title">1단계 · 차트를 관찰하세요</div>', unsafe_allow_html=True)

left, right = st.columns([1.95, 1], gap="large")

with left:
    st.plotly_chart(plot_mystery_chart(game_round), use_container_width=True)

with right:
    st.markdown("### 🔎 탐정 노트")
    st.markdown(
        """
        <div class="caption-box">
        정답을 바로 맞히는 것보다 중요한 것은 <b>근거 있는 예측</b>입니다.<br>
        이동평균선, 최근 흐름, 거래량, 변동성을 하나씩 확인하세요.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(" ")

    if game_round["show_hints"]:
        hint_cols = st.columns(2)
        hint_items = [signals["trend"], signals["volume"], signals["risk"], signals["momentum"]]
        for idx, item in enumerate(hint_items):
            emoji, title, note = item
            with hint_cols[idx % 2]:
                render_card(title, emoji, note)
    else:
        render_card("힌트 잠금", "🔐", "퀀트 모드에서는 힌트 없이 차트와 숫자를 직접 해석합니다.")
        raw = signals["raw"]
        st.markdown("#### 직접 볼 숫자")
        st.write(f"- 최근 5거래일 수익률: **{percent_text(raw['return5'])}**")
        st.write(f"- 최근 20거래일 수익률: **{percent_text(raw['return20'])}**")
        st.write(f"- 20일 변동성: **{percent_text(raw['vol20'])}**")


# =========================================================
# 2단계: 예측 제출
# =========================================================

if not st.session_state.revealed:
    st.markdown('<div class="step-title">2단계 · 예측을 제출하세요</div>', unsafe_allow_html=True)

    with st.form("prediction_form"):
        p_col1, p_col2, p_col3 = st.columns([1.15, 1, 1])

        with p_col1:
            prediction_label = st.radio(
                "다음 방향",
                ["📈 상승", "➡️ 횡보", "📉 하락"],
                horizontal=True,
                help="상승/하락은 난이도별 기준 이상 움직였을 때만 인정됩니다.",
            )

        with p_col2:
            confidence = st.slider(
                "자신감",
                min_value=1,
                max_value=5,
                value=3,
                help="확신이 높을수록 맞히면 보너스, 틀리면 감점이 커집니다.",
            )

        with p_col3:
            stake_pct = st.slider(
                "투자 코인 비중",
                min_value=10,
                max_value=100,
                value=40,
                step=10,
                help="보유 코인 중 이번 예측에 걸 비중입니다. 실제 투자가 아닌 게임 포인트입니다.",
            )

        evidence = st.multiselect(
            "예측 근거를 고르세요. 너무 많이 고르기보다 핵심 근거 2~3개를 고르는 것이 좋습니다.",
            EVIDENCE_OPTIONS,
        )

        memo = st.text_area(
            "한 줄 예측 메모",
            placeholder="예: 20일 평균선 위에서 가격이 버티고 있고 거래량도 늘어서 상승을 예상했다.",
            height=90,
        )

        submitted = st.form_submit_button(
            "🚀 예측 제출하고 결과 보기",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        prediction = prediction_to_plain(prediction_label)
        actual, return_rate, start_price, end_price = judge_actual(visible_df, hidden_df, threshold)

        stake_coins = st.session_state.coins * stake_pct / 100
        coin_delta, game_return = simulate_coin_result(prediction, return_rate, stake_coins, threshold)
        final_score, correct = calculate_score(
            prediction=prediction,
            actual=actual,
            confidence=confidence,
            stake_pct=stake_pct,
            evidence_count=len(evidence),
            memo=memo,
            coin_delta=coin_delta,
        )

        st.session_state.coins = max(st.session_state.coins + coin_delta, 0)
        st.session_state.total_score += final_score
        st.session_state.round_no += 1

        result = {
            "라운드": st.session_state.round_no,
            "종목": game_round["ticker"] if not game_round["blind_mode"] else f"비밀 종목 #{game_round['round_id']}",
            "난이도": game_round["difficulty"],
            "예측": prediction,
            "실제": actual,
            "정답": correct,
            "실제 수익률": return_rate,
            "자신감": confidence,
            "코인 비중": stake_pct,
            "코인 변화": coin_delta,
            "점수": final_score,
            "근거": ", ".join(evidence),
            "메모": memo,
        }

        st.session_state.history.append(result)
        st.session_state.last_result = result
        st.session_state.revealed = True
        st.rerun()

else:
    result = st.session_state.last_result
    correct = result["정답"]
    prediction = result["예측"]
    actual = result["실제"]
    return_rate = result["실제 수익률"]
    coin_delta = result["코인 변화"]
    final_score = result["점수"]
    confidence = result["자신감"]
    stake_pct = result["코인 비중"]

    st.markdown('<div class="step-title">3단계 · 실제 결과를 확인하세요</div>', unsafe_allow_html=True)

    result_class = "result-good" if correct else "result-bad"
    result_title = "정답입니다!" if correct else "빗나갔습니다"
    result_note = "근거를 복기해서 다음 라운드에 적용해보세요."

    st.markdown(
        f"""
        <div class="{result_class}">
            <div class="small-label">RESULT</div>
            <div class="big-value">{safe_text(result_title)}</div>
            <div class="sub-note">내 예측은 {safe_text(prediction)}, 실제 결과는 {safe_text(actual)}입니다. {safe_text(result_note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if correct and st.session_state.celebrated_round_id != game_round["round_id"]:
        st.balloons()
        st.session_state.celebrated_round_id = game_round["round_id"]

    r1, r2, r3, r4, r5 = st.columns(5)
    r1.metric("내 예측", prediction)
    r2.metric("실제 결과", actual)
    r3.metric("실제 수익률", percent_text(return_rate))
    r4.metric("코인 변화", f"{coin_delta:+,.1f}")
    r5.metric("획득 점수", f"{final_score:,.1f}")

    st.plotly_chart(plot_reveal_chart(game_round), use_container_width=True)

    st.markdown('<div class="step-title">4단계 · 복기하세요</div>', unsafe_allow_html=True)

    feedback = build_feedback(prediction, actual, return_rate, threshold, confidence, stake_pct, signals)
    f_col1, f_col2 = st.columns([1.15, 1], gap="large")

    with f_col1:
        st.markdown("### 🧠 피드백")
        for item in feedback:
            st.write(f"- {item}")

        if result["근거"]:
            st.markdown("### 내가 선택한 근거")
            st.write(result["근거"])

        if result["메모"].strip():
            st.markdown("### 나의 메모")
            st.write(result["메모"])

    with f_col2:
        st.markdown("### 💬 모둠 토론 질문")
        st.markdown(
            """
            1. 맞혔다면, 근거가 좋아서 맞힌 것인가 우연히 맞힌 것인가?
            2. 틀렸다면, 어떤 신호를 과대평가했는가?
            3. 투자 코인 비중은 적절했는가?
            4. 같은 차트를 다시 본다면 예측을 바꿀 것인가?
            """
        )

        if st.button("🎲 다음 라운드 시작", type="primary", use_container_width=True):
            new_round = make_round(price_df, ticker, stock_name, difficulty, blind_mode)
            if new_round is not None:
                st.session_state.game_round = new_round
                st.session_state.config_key = config_key
                st.session_state.revealed = False
                st.session_state.last_result = None
                st.rerun()


# =========================================================
# 기록과 학습 자료
# =========================================================

st.markdown("---")

hist_col, learn_col = st.columns([1.25, 1], gap="large")

with hist_col:
    st.markdown("## 📜 예측 기록")
    if st.session_state.history:
        history_df = pd.DataFrame(st.session_state.history)
        display_df = history_df.copy()
        display_df["실제 수익률"] = display_df["실제 수익률"].map(lambda x: percent_text(x))
        display_df["코인 비중"] = display_df["코인 비중"].map(lambda x: f"{x}%")
        display_df["코인 변화"] = display_df["코인 변화"].map(lambda x: f"{x:+,.1f}")
        display_df["점수"] = display_df["점수"].map(lambda x: f"{x:,.1f}")
        st.dataframe(
            display_df[["라운드", "종목", "난이도", "예측", "실제", "정답", "실제 수익률", "코인 변화", "점수"]],
            use_container_width=True,
            hide_index=True,
        )

        score_fig = go.Figure()
        score_fig.add_trace(
            go.Scatter(
                x=history_df["라운드"],
                y=history_df["점수"],
                mode="lines+markers",
                name="라운드 점수",
            )
        )
        score_fig.update_layout(
            height=330,
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis_title="라운드",
            yaxis_title="점수",
            hovermode="x unified",
        )
        st.plotly_chart(score_fig, use_container_width=True)

        csv = history_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "예측 기록 CSV 다운로드",
            data=csv,
            file_name="stock_detective_history.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("아직 예측 기록이 없습니다. 첫 라운드를 제출해보세요.")

with learn_col:
    st.markdown("## 📚 오늘의 주식 개념")

    with st.expander("이동평균선", expanded=True):
        st.write(
            "이동평균선은 일정 기간의 평균 가격입니다. 20일선은 최근 20거래일의 평균 가격이고, "
            "60일선은 더 긴 흐름을 보여줍니다. 주가가 평균선 위에 있으면 강한 흐름으로 해석할 수 있지만, "
            "미래를 보장하는 공식은 아닙니다."
        )

    with st.expander("거래량"):
        st.write(
            "거래량은 사고팔린 주식 수입니다. 가격이 오르면서 거래량이 늘면 많은 사람이 관심을 보인 것으로 "
            "해석할 수 있습니다. 반대로 가격이 떨어지며 거래량이 늘면 매도 압력이 강했을 가능성도 있습니다."
        )

    with st.expander("변동성"):
        st.write(
            "변동성은 가격이 얼마나 크게 흔들리는지를 뜻합니다. 변동성이 크면 수익 기회도 커질 수 있지만, "
            "손실 위험도 함께 커집니다. 그래서 예측만큼이나 투자 비중 조절이 중요합니다."
        )

    with st.expander("횡보"):
        st.write(
            "횡보는 가격이 크게 오르거나 내리지 않고 일정 범위 안에서 움직이는 상태입니다. "
            "이 게임에서는 난이도별 기준 안쪽의 움직임을 횡보로 판정합니다."
        )

    with st.expander("수익률"):
        st.write(
            "수익률은 처음 가격에 비해 마지막 가격이 얼마나 변했는지를 나타냅니다. "
            "예를 들어 100에서 105가 되면 수익률은 5%입니다."
        )

st.caption("Made for classroom stock-data literacy · Streamlit + yfinance + Plotly")
