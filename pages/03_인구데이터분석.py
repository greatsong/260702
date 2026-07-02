# app.py
# ============================================================
# 🧭 청소년을 위한 인구 데이터 분석 대시보드
# - Streamlit Cloud 호환
# - 행정안전부/주민등록 연령별 인구현황 월간 CSV 형식 대응
# - Plotly 기반 인터랙티브 시각화
# ============================================================

import os
import re
import csv
import sys
import glob
from io import BytesIO

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


# ------------------------------------------------------------
# 0. 페이지 기본 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="인구 데이터 분석 대시보드",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="expanded",
)

csv.field_size_limit(sys.maxsize)


# ------------------------------------------------------------
# 1. CSS: Streamlit 기본 UI를 조금 더 예쁘게
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    .main {
        background: linear-gradient(180deg, #f8fbff 0%, #ffffff 45%, #f7f9fc 100%);
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    .title-box {
        padding: 1.4rem 1.6rem;
        border-radius: 24px;
        background: linear-gradient(135deg, #e9f2ff 0%, #fff7e6 100%);
        border: 1px solid rgba(0, 0, 0, 0.06);
        margin-bottom: 1.2rem;
    }
    .title-box h1 {
        margin-bottom: 0.35rem;
    }
    .soft-card {
        padding: 1.1rem 1.2rem;
        border-radius: 20px;
        background: #ffffff;
        border: 1px solid rgba(0, 0, 0, 0.06);
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        margin-bottom: 1rem;
    }
    .metric-help {
        color: #64748b;
        font-size: 0.92rem;
        line-height: 1.55;
    }
    .big-number {
        font-size: 2.1rem;
        font-weight: 800;
        color: #0f172a;
    }
    .mini-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.4rem;
    }
    .insight {
        padding: 1rem 1.1rem;
        border-radius: 18px;
        background: #fff8e6;
        border-left: 6px solid #f59e0b;
        line-height: 1.7;
        margin-bottom: 0.9rem;
    }
    .good {
        padding: 1rem 1.1rem;
        border-radius: 18px;
        background: #ecfdf5;
        border-left: 6px solid #10b981;
        line-height: 1.7;
        margin-bottom: 0.9rem;
    }
    .warn {
        padding: 1rem 1.1rem;
        border-radius: 18px;
        background: #fff1f2;
        border-left: 6px solid #f43f5e;
        line-height: 1.7;
        margin-bottom: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# 2. 유틸 함수
# ------------------------------------------------------------
def clean_number(x):
    """문자열 숫자에서 쉼표를 제거하고 숫자로 변환한다."""
    if pd.isna(x):
        return np.nan
    return pd.to_numeric(str(x).replace(",", "").strip(), errors="coerce")


def extract_age(col_name):
    """열 이름에서 나이를 추출한다. 100세 이상은 100으로 처리한다."""
    if "100세 이상" in col_name:
        return 100
    match = re.search(r"_(\d+)세$", col_name)
    if match:
        return int(match.group(1))
    return None


def extract_region_code(region_text):
    match = re.search(r"\((\d+)\)", str(region_text))
    return match.group(1) if match else ""


def clean_region_name(region_text):
    return re.sub(r"\(\d+\)", "", str(region_text)).strip()


def infer_region_level(region_name):
    """
    행정구역명 단어 수를 기반으로 대략적인 행정 수준을 추정한다.
    예: 서울특별시 -> 시도
        서울특별시 종로구 -> 시군구
        서울특별시 종로구 사직동 -> 읍면동
    """
    parts = str(region_name).split()
    if len(parts) <= 1:
        return "시도"
    elif len(parts) == 2:
        return "시군구"
    return "읍면동"


def weighted_median_age(age_df, value_col="전체"):
    """연령별 인구로 가중 중앙연령을 계산한다."""
    temp = age_df[["나이", value_col]].dropna().copy()
    temp = temp.sort_values("나이")
    total = temp[value_col].sum()
    if total <= 0:
        return np.nan
    temp["누적"] = temp[value_col].cumsum()
    return temp.loc[temp["누적"] >= total / 2, "나이"].iloc[0]


def age_group(age):
    """교육용 연령대 구분"""
    if age <= 4:
        return "0~4세 영유아"
    elif age <= 14:
        return "5~14세 아동"
    elif age <= 19:
        return "15~19세 청소년"
    elif age <= 29:
        return "20~29세 청년"
    elif age <= 39:
        return "30~39세 가족형성기"
    elif age <= 49:
        return "40~49세 중년 진입"
    elif age <= 64:
        return "50~64세 중장년"
    else:
        return "65세 이상 고령층"


def format_int(n):
    if pd.isna(n):
        return "-"
    return f"{int(round(n)):,}"


def format_pct(x):
    if pd.isna(x):
        return "-"
    return f"{x:.1f}%"


# ------------------------------------------------------------
# 3. 데이터 로딩
# ------------------------------------------------------------
@st.cache_data(show_spinner=False)
def read_population_csv_from_bytes(file_bytes):
    """
    CSV 파일을 읽는다.
    - cp949/euc-kr/utf-8-sig 순서로 시도
    - 일부 행 깨짐이 있을 수 있어 on_bad_lines='skip' 적용
    """
    encodings = ["cp949", "euc-kr", "utf-8-sig", "utf-8"]
    last_error = None

    for enc in encodings:
        try:
            buffer = BytesIO(file_bytes)
            df = pd.read_csv(
                buffer,
                encoding=enc,
                engine="python",
                on_bad_lines="skip",
            )
            return df, enc
        except Exception as e:
            last_error = e

    raise ValueError(f"CSV 파일을 읽지 못했습니다. 마지막 오류: {last_error}")


@st.cache_data(show_spinner=False)
def preprocess_population(df):
    df = df.copy()

    if "행정구역" not in df.columns:
        raise ValueError("CSV에 '행정구역' 열이 없습니다. 행정안전부 연령별 인구현황 월간 CSV인지 확인해주세요.")

    df["행정구역명"] = df["행정구역"].apply(clean_region_name)
    df["행정코드"] = df["행정구역"].apply(extract_region_code)
    df["행정수준"] = df["행정구역명"].apply(infer_region_level)

    # 숫자 열 변환
    for col in df.columns:
        if col not in ["행정구역", "행정구역명", "행정코드", "행정수준"]:
            df[col] = df[col].apply(clean_number)

    # 월 정보 추출
    month_match = re.search(r"(\d{4}년\d{2}월)", " ".join(df.columns))
    data_month = month_match.group(1) if month_match else "자료 기준월 확인 필요"

    return df, data_month


def find_default_csv():
    """Streamlit Cloud에 CSV를 같이 올렸을 때 자동으로 찾는다."""
    candidates = glob.glob("*.csv") + glob.glob("./*.csv")
    if candidates:
        return candidates[0]
    return None


def get_age_columns(df, sex="계"):
    pattern = f"_{sex}_"
    cols = []
    for col in df.columns:
        if pattern in col:
            age = extract_age(col)
            if age is not None:
                cols.append((age, col))
    cols = sorted(cols, key=lambda x: x[0])
    return cols


def make_age_df(row, df):
    total_cols = get_age_columns(df, "계")
    male_cols = get_age_columns(df, "남")
    female_cols = get_age_columns(df, "여")

    rows = []
    for age, total_col in total_cols:
        male_col = dict(male_cols).get(age)
        female_col = dict(female_cols).get(age)

        total = row.get(total_col, np.nan)
        male = row.get(male_col, np.nan) if male_col else np.nan
        female = row.get(female_col, np.nan) if female_col else np.nan

        rows.append({
            "나이": age,
            "연령표시": "100세 이상" if age == 100 else f"{age}세",
            "전체": total,
            "남자": male,
            "여자": female,
            "연령대": age_group(age),
        })

    return pd.DataFrame(rows)


def make_region_metrics(df):
    """지역별 핵심 지표 테이블 생성"""
    total_cols = dict(get_age_columns(df, "계"))

    records = []
    for _, row in df.iterrows():
        values = {age: row.get(col, 0) for age, col in total_cols.items()}

        total_pop = np.nansum(list(values.values()))
        pop_0 = values.get(0, 0)
        pop_1 = values.get(1, 0)
        pop_1_4 = np.nanmean([values.get(a, np.nan) for a in range(1, 5)])

        youth_0_14 = np.nansum([values.get(a, 0) for a in range(0, 15)])
        school_6_18 = np.nansum([values.get(a, 0) for a in range(6, 19)])
        working_15_64 = np.nansum([values.get(a, 0) for a in range(15, 65)])
        elderly_65 = np.nansum([values.get(a, 0) for a in range(65, 101)])
        parent_30_39 = np.nansum([values.get(a, 0) for a in range(30, 40)])

        aging_index = elderly_65 / youth_0_14 * 100 if youth_0_14 > 0 else np.nan
        dependency = (youth_0_14 + elderly_65) / working_15_64 * 100 if working_15_64 > 0 else np.nan
        old_dependency = elderly_65 / working_15_64 * 100 if working_15_64 > 0 else np.nan
        child_share = youth_0_14 / total_pop * 100 if total_pop > 0 else np.nan
        elderly_share = elderly_65 / total_pop * 100 if total_pop > 0 else np.nan
        infant_rebound = (pop_0 / pop_1 - 1) * 100 if pop_1 > 0 else np.nan
        infant_vs_1_4 = (pop_0 / pop_1_4 - 1) * 100 if pop_1_4 and pop_1_4 > 0 else np.nan
        infant_per_parent = pop_0 / parent_30_39 * 1000 if parent_30_39 > 0 else np.nan

        records.append({
            "행정구역명": row["행정구역명"],
            "행정코드": row["행정코드"],
            "행정수준": row["행정수준"],
            "총인구": total_pop,
            "0세 인구": pop_0,
            "1세 인구": pop_1,
            "1~4세 평균": pop_1_4,
            "0~14세": youth_0_14,
            "6~18세": school_6_18,
            "15~64세": working_15_64,
            "65세 이상": elderly_65,
            "30~39세": parent_30_39,
            "유소년비율": child_share,
            "고령층비율": elderly_share,
            "고령화지수": aging_index,
            "총부양비": dependency,
            "노년부양비": old_dependency,
            "0세/1세 증감률": infant_rebound,
            "0세/1~4세평균 증감률": infant_vs_1_4,
            "30~39세 1천명당 0세": infant_per_parent,
        })

    return pd.DataFrame(records)


# ------------------------------------------------------------
# 4. 헤더
# ------------------------------------------------------------
st.markdown(
    """
    <div class="title-box">
        <h1>🌏 인구 데이터 분석 대시보드</h1>
        <p>
        연령별 인구 데이터를 통해 우리 지역의 <b>인구 구조</b>, <b>고령화</b>, 
        <b>청소년 인구</b>, 그리고 <b>최근 출생률 반등 신호</b>를 탐구합니다.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# 5. 사이드바: 데이터 입력
# ------------------------------------------------------------
st.sidebar.title("📁 데이터 불러오기")

uploaded_file = st.sidebar.file_uploader(
    "연령별 인구현황 CSV 업로드",
    type=["csv"],
    help="행정안전부 주민등록 연령별 인구현황 월간 CSV 형식을 권장합니다.",
)

default_csv = find_default_csv()

file_bytes = None
data_source_name = None

if uploaded_file is not None:
    file_bytes = uploaded_file.read()
    data_source_name = uploaded_file.name
elif default_csv:
    with open(default_csv, "rb") as f:
        file_bytes = f.read()
    data_source_name = default_csv

if file_bytes is None:
    st.info(
        """
        👋 왼쪽 사이드바에서 CSV 파일을 업로드해주세요.

        추천 데이터 형식은 다음과 같습니다.

        - 행정구역
        - 2026년06월_계_총인구수
        - 2026년06월_계_0세 ~ 100세 이상
        - 2026년06월_남_0세 ~ 100세 이상
        - 2026년06월_여_0세 ~ 100세 이상
        """
    )
    st.stop()


try:
    raw_df, encoding_used = read_population_csv_from_bytes(file_bytes)
    pop_df, data_month = preprocess_population(raw_df)
    metrics_df = make_region_metrics(pop_df)
except Exception as e:
    st.error("데이터를 읽는 중 문제가 발생했습니다.")
    st.exception(e)
    st.stop()


st.sidebar.success(f"✅ 데이터 로딩 완료: {data_source_name}")
st.sidebar.caption(f"인코딩: {encoding_used} / 기준월: {data_month}")

with st.sidebar.expander("⚠️ CSV 읽기 안내"):
    st.write(
        """
        일부 행이 줄바꿈 또는 쉼표 문제로 깨져 있을 경우 앱은 오류를 막기 위해 해당 행을 건너뜁니다.
        중요한 분석에서는 원본 CSV를 한 번 더 확인하는 것이 좋습니다.
        """
    )


# ------------------------------------------------------------
# 6. 사이드바: 필터
# ------------------------------------------------------------
st.sidebar.title("🔎 분석 조건")

level_options = ["시도", "시군구", "읍면동"]
available_levels = [x for x in level_options if x in pop_df["행정수준"].unique()]

selected_level = st.sidebar.selectbox(
    "행정구역 수준 선택",
    available_levels,
    index=0 if "시도" in available_levels else 0,
)

region_candidates = pop_df[pop_df["행정수준"] == selected_level]["행정구역명"].tolist()

selected_region = st.sidebar.selectbox(
    "분석할 지역 선택",
    region_candidates,
)

selected_row = pop_df.loc[pop_df["행정구역명"] == selected_region].iloc[0]
age_df = make_age_df(selected_row, pop_df)

selected_metric_row = metrics_df.loc[metrics_df["행정구역명"] == selected_region].iloc[0]


# ------------------------------------------------------------
# 7. 핵심 지표 계산
# ------------------------------------------------------------
total_pop = selected_metric_row["총인구"]
age_0 = selected_metric_row["0세 인구"]
age_1 = selected_metric_row["1세 인구"]
youth_0_14 = selected_metric_row["0~14세"]
school_6_18 = selected_metric_row["6~18세"]
working_15_64 = selected_metric_row["15~64세"]
elderly_65 = selected_metric_row["65세 이상"]

median_age = weighted_median_age(age_df)
aging_index = selected_metric_row["고령화지수"]
dependency = selected_metric_row["총부양비"]
rebound_0_1 = selected_metric_row["0세/1세 증감률"]
rebound_0_avg = selected_metric_row["0세/1~4세평균 증감률"]


# ------------------------------------------------------------
# 8. 탭 구성
# ------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📌 한눈에 보기",
    "🧬 인구 피라미드",
    "🧒 청소년 렌즈",
    "👶 출생 반등 탐구",
    "🗺️ 지역 비교",
    "📚 수업 해설",
])


# ------------------------------------------------------------
# TAB 1. 한눈에 보기
# ------------------------------------------------------------
with tab1:
    st.subheader(f"📌 {selected_region} 인구 구조 한눈에 보기")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총인구", f"{format_int(total_pop)}명")
    c2.metric("중앙연령", f"{median_age:.0f}세" if not pd.isna(median_age) else "-")
    c3.metric("65세 이상", f"{format_int(elderly_65)}명", f"{selected_metric_row['고령층비율']:.1f}%")
    c4.metric("0~14세", f"{format_int(youth_0_14)}명", f"{selected_metric_row['유소년비율']:.1f}%")

    st.markdown("### 🎂 연령별 인구 분포")

    fig_age = px.line(
        age_df,
        x="나이",
        y="전체",
        markers=True,
        title=f"{selected_region} 연령별 인구 분포",
        labels={"나이": "나이", "전체": "인구 수"},
    )
    fig_age.update_traces(line=dict(width=3), marker=dict(size=5))
    fig_age.update_layout(
        hovermode="x unified",
        height=460,
        title_x=0.02,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    st.plotly_chart(fig_age, use_container_width=True)

    group_df = (
        age_df.groupby("연령대", as_index=False)["전체"]
        .sum()
    )
    order = [
        "0~4세 영유아",
        "5~14세 아동",
        "15~19세 청소년",
        "20~29세 청년",
        "30~39세 가족형성기",
        "40~49세 중년 진입",
        "50~64세 중장년",
        "65세 이상 고령층",
    ]
    group_df["연령대"] = pd.Categorical(group_df["연령대"], categories=order, ordered=True)
    group_df = group_df.sort_values("연령대")

    col_a, col_b = st.columns([1.1, 0.9])

    with col_a:
        fig_group = px.bar(
            group_df,
            x="연령대",
            y="전체",
            text="전체",
            title="연령대별 인구",
            labels={"전체": "인구 수"},
        )
        fig_group.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig_group.update_layout(
            height=430,
            xaxis_tickangle=-20,
            title_x=0.02,
            margin=dict(l=20, r=20, t=60, b=80),
        )
        st.plotly_chart(fig_group, use_container_width=True)

    with col_b:
        fig_pie = px.pie(
            group_df,
            names="연령대",
            values="전체",
            title="연령대 구성 비율",
            hole=0.45,
        )
        fig_pie.update_layout(height=430, title_x=0.02)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown(
        f"""
        <div class="insight">
        <b>🧠 읽는 법</b><br>
        인구 그래프에서 특정 나이대가 볼록하게 튀어나오면 그 세대의 인구가 많다는 뜻입니다.
        예를 들어 50대와 60대가 두껍고 0~10대가 얇다면, 앞으로 학교·노동시장·복지 제도가
        모두 달라질 가능성이 큽니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# TAB 2. 인구 피라미드
# ------------------------------------------------------------
with tab2:
    st.subheader(f"🧬 {selected_region} 인구 피라미드")

    pyramid_df = age_df.copy()
    pyramid_df["남자_음수"] = -pyramid_df["남자"]

    fig_pyramid = go.Figure()

    fig_pyramid.add_trace(go.Bar(
        y=pyramid_df["연령표시"],
        x=pyramid_df["남자_음수"],
        name="남자",
        orientation="h",
        hovertemplate="남자 %{customdata:,}명<extra></extra>",
        customdata=pyramid_df["남자"],
    ))

    fig_pyramid.add_trace(go.Bar(
        y=pyramid_df["연령표시"],
        x=pyramid_df["여자"],
        name="여자",
        orientation="h",
        hovertemplate="여자 %{x:,}명<extra></extra>",
    ))

    max_x = np.nanmax([pyramid_df["남자"].max(), pyramid_df["여자"].max()])
    tick_vals = np.linspace(-max_x, max_x, 7)
    tick_text = [f"{abs(int(x)):,}" for x in tick_vals]

    fig_pyramid.update_layout(
        title=f"{selected_region} 성별·연령별 인구 피라미드",
        barmode="relative",
        bargap=0.04,
        height=720,
        title_x=0.02,
        xaxis=dict(
            title="인구 수",
            tickvals=tick_vals,
            ticktext=tick_text,
        ),
        yaxis=dict(title="나이"),
        legend=dict(orientation="h", y=1.04, x=0.02),
        margin=dict(l=20, r=20, t=80, b=30),
    )

    st.plotly_chart(fig_pyramid, use_container_width=True)

    male_total = age_df["남자"].sum()
    female_total = age_df["여자"].sum()
    sex_ratio = male_total / female_total * 100 if female_total > 0 else np.nan

    c1, c2, c3 = st.columns(3)
    c1.metric("남자 인구", f"{format_int(male_total)}명")
    c2.metric("여자 인구", f"{format_int(female_total)}명")
    c3.metric("성비", f"{sex_ratio:.1f}", help="여자 100명당 남자 수")

    st.markdown(
        """
        <div class="soft-card">
        <div class="mini-title">🔍 피라미드를 읽는 핵심 질문</div>
        <div class="metric-help">
        1. 아래쪽이 넓은가요? → 어린 인구가 많아 앞으로 성장 가능성이 큽니다.<br>
        2. 가운데가 두꺼운가요? → 현재 일하고 소비하는 생산가능인구가 많습니다.<br>
        3. 위쪽이 넓은가요? → 고령화가 진행되어 의료·돌봄·연금 수요가 커질 수 있습니다.<br>
        4. 남녀 차이가 큰 연령대가 있나요? → 군 복무, 산업 구조, 기대수명 차이 등을 생각해볼 수 있습니다.
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# TAB 3. 청소년 렌즈
# ------------------------------------------------------------
with tab3:
    st.subheader(f"🧒 {selected_region} 청소년 인구 분석")

    youth_df = age_df[(age_df["나이"] >= 6) & (age_df["나이"] <= 18)].copy()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("초·중·고 학령기", f"{format_int(school_6_18)}명")
    c2.metric("6~11세", f"{format_int(age_df[(age_df['나이'] >= 6) & (age_df['나이'] <= 11)]['전체'].sum())}명")
    c3.metric("12~14세", f"{format_int(age_df[(age_df['나이'] >= 12) & (age_df['나이'] <= 14)]['전체'].sum())}명")
    c4.metric("15~18세", f"{format_int(age_df[(age_df['나이'] >= 15) & (age_df['나이'] <= 18)]['전체'].sum())}명")

    fig_youth = px.bar(
        youth_df,
        x="연령표시",
        y="전체",
        text="전체",
        title="6~18세 학령기 인구",
        labels={"연령표시": "나이", "전체": "인구 수"},
    )
    fig_youth.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig_youth.update_layout(
        height=460,
        title_x=0.02,
        margin=dict(l=20, r=20, t=60, b=30),
    )
    st.plotly_chart(fig_youth, use_container_width=True)

    st.markdown("### 🏫 학교와 지역사회 관점에서 생각하기")

    st.markdown(
        """
        <div class="good">
        <b>청소년 인구는 단순한 숫자가 아닙니다.</b><br>
        청소년 인구가 줄어들면 학교 통폐합, 학급 수 감소, 지역 학원·도서관·체육시설 수요 변화가 나타날 수 있습니다.
        반대로 특정 지역에서 청소년 인구가 유지되거나 늘어난다면, 그 지역은 주거·교육·교통 측면에서
        젊은 가족에게 매력적인 조건을 갖고 있을 가능성이 있습니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

    youth_share = school_6_18 / total_pop * 100 if total_pop > 0 else np.nan
    st.info(
        f"📌 {selected_region}의 6~18세 학령기 인구 비율은 전체 인구의 약 {youth_share:.1f}%입니다."
    )


# ------------------------------------------------------------
# TAB 4. 출생 반등 탐구
# ------------------------------------------------------------
with tab4:
    st.subheader(f"👶 {selected_region} 출생 반등 신호 읽기")

    infant_df = age_df[age_df["나이"].between(0, 5)].copy()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("0세 인구", f"{format_int(age_0)}명")
    c2.metric("1세 인구", f"{format_int(age_1)}명")
    c3.metric("0세 / 1세 증감률", format_pct(rebound_0_1))
    c4.metric("0세 / 1~4세 평균", format_pct(rebound_0_avg))

    fig_infant = px.bar(
        infant_df,
        x="연령표시",
        y="전체",
        text="전체",
        title="0~5세 인구 비교",
        labels={"연령표시": "나이", "전체": "인구 수"},
    )
    fig_infant.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig_infant.update_layout(
        height=460,
        title_x=0.02,
        margin=dict(l=20, r=20, t=60, b=30),
    )
    st.plotly_chart(fig_infant, use_container_width=True)

    parent_df = age_df[age_df["나이"].between(25, 44)].copy()
    fig_parent = px.area(
        parent_df,
        x="나이",
        y="전체",
        markers=True,
        title="25~44세 인구: 결혼·출산 가능성이 높은 연령대의 규모",
        labels={"나이": "나이", "전체": "인구 수"},
    )
    fig_parent.update_layout(
        height=420,
        hovermode="x unified",
        title_x=0.02,
        margin=dict(l=20, r=20, t=60, b=30),
    )
    st.plotly_chart(fig_parent, use_container_width=True)

    if not pd.isna(rebound_0_1) and rebound_0_1 > 5:
        st.markdown(
            f"""
            <div class="good">
            <b>✅ 반등 신호가 보입니다.</b><br>
            이 지역은 0세 인구가 1세 인구보다 약 <b>{rebound_0_1:.1f}%</b> 많습니다.
            이는 최근 출생아 증가, 젊은 가족 유입, 신축 주거지 입주 등의 가능성을 생각해볼 수 있는 신호입니다.
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif not pd.isna(rebound_0_1) and rebound_0_1 < -5:
        st.markdown(
            f"""
            <div class="warn">
            <b>⚠️ 반등 신호가 약합니다.</b><br>
            이 지역은 0세 인구가 1세 인구보다 약 <b>{abs(rebound_0_1):.1f}%</b> 적습니다.
            출생 감소, 젊은 가족 유출, 주거비 부담, 보육 환경 등을 함께 살펴볼 필요가 있습니다.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="insight">
            <b>➖ 뚜렷한 반등 또는 감소 신호가 크지 않습니다.</b><br>
            0세와 1세 인구가 비슷하다는 것은 최근 출생 또는 영유아 유입 흐름이 비교적 안정적일 수 있음을 뜻합니다.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        ### 🧠 중요한 해석 주의점

        이 대시보드의 0세 인구는 **출생아 수 자체가 아닙니다.**  
        주민등록 기준의 특정 시점 인구이기 때문에 다음 요인이 섞여 있습니다.

        - 👶 실제 출생 증가 또는 감소
        - 🚚 영유아가 있는 가족의 지역 이동
        - 🏘️ 신축 아파트 입주, 전세·매매 가격 변화
        - 🏥 산부인과·소아과·보육 인프라
        - 🧾 전입·전출 신고 시점 차이

        그래서 “0세가 늘었다 = 출산율이 반드시 올랐다”라고 단정하면 안 됩니다.  
        대신 **출생 반등을 의심해볼 만한 탐색 지표**로 활용하는 것이 좋습니다.
        """
    )


# ------------------------------------------------------------
# TAB 5. 지역 비교
# ------------------------------------------------------------
with tab5:
    st.subheader("🗺️ 지역별 비교 분석")

    compare_level = st.selectbox(
        "비교할 행정구역 수준",
        available_levels,
        index=available_levels.index(selected_level) if selected_level in available_levels else 0,
        key="compare_level",
    )

    compare_metric = st.selectbox(
        "비교할 지표",
        [
            "총인구",
            "0세 인구",
            "6~18세",
            "유소년비율",
            "고령층비율",
            "고령화지수",
            "총부양비",
            "0세/1세 증감률",
            "0세/1~4세평균 증감률",
            "30~39세 1천명당 0세",
        ],
    )

    top_n = st.slider("상위 몇 개 지역을 볼까요?", 5, 30, 15)

    compare_df = metrics_df[metrics_df["행정수준"] == compare_level].copy()
    compare_df = compare_df.dropna(subset=[compare_metric])
    compare_df = compare_df.sort_values(compare_metric, ascending=False).head(top_n)

    fig_compare = px.bar(
        compare_df.sort_values(compare_metric),
        x=compare_metric,
        y="행정구역명",
        orientation="h",
        text=compare_metric,
        title=f"{compare_level} 기준 상위 {top_n}개 지역: {compare_metric}",
        labels={"행정구역명": "지역"},
    )

    if "비율" in compare_metric or "증감률" in compare_metric or "지수" in compare_metric or "부양비" in compare_metric:
        fig_compare.update_traces(texttemplate="%{text:.1f}")
    else:
        fig_compare.update_traces(texttemplate="%{text:,.0f}")

    fig_compare.update_layout(
        height=max(430, top_n * 32),
        title_x=0.02,
        margin=dict(l=20, r=20, t=60, b=30),
    )
    st.plotly_chart(fig_compare, use_container_width=True)

    st.markdown("### 📋 비교 데이터")
    st.dataframe(
        compare_df[
            [
                "행정구역명",
                "총인구",
                "0세 인구",
                "6~18세",
                "유소년비율",
                "고령층비율",
                "고령화지수",
                "총부양비",
                "0세/1세 증감률",
                "0세/1~4세평균 증감률",
                "30~39세 1천명당 0세",
            ]
        ].style.format({
            "총인구": "{:,.0f}",
            "0세 인구": "{:,.0f}",
            "6~18세": "{:,.0f}",
            "유소년비율": "{:.1f}",
            "고령층비율": "{:.1f}",
            "고령화지수": "{:.1f}",
            "총부양비": "{:.1f}",
            "0세/1세 증감률": "{:.1f}",
            "0세/1~4세평균 증감률": "{:.1f}",
            "30~39세 1천명당 0세": "{:.1f}",
        }),
        use_container_width=True,
    )


# ------------------------------------------------------------
# TAB 6. 수업 해설
# ------------------------------------------------------------
with tab6:
    st.subheader("📚 청소년을 위한 인구 데이터 읽기 수업")

    st.markdown(
        """
        ### 1️⃣ 인구 피라미드는 미래를 보여주는 지도입니다

        인구 피라미드는 단순히 “지금 몇 살이 몇 명인가”를 보여주는 그래프가 아닙니다.  
        이 그래프는 앞으로의 학교, 일자리, 병원, 복지, 주거 정책을 예측하게 해주는 **미래 지도**입니다.

        - 아래쪽이 얇다 → 앞으로 학생 수가 줄어들 가능성
        - 가운데가 두껍다 → 현재 경제활동 인구가 많음
        - 위쪽이 두껍다 → 의료·돌봄·연금 부담 증가 가능성
        """
    )

    st.markdown(
        """
        ### 2️⃣ 고령화지수란?

        **고령화지수 = 65세 이상 인구 ÷ 0~14세 인구 × 100**

        예를 들어 고령화지수가 200이면, 어린이 100명당 노인이 200명 있다는 뜻입니다.  
        이 숫자가 높을수록 지역사회는 다음 질문을 고민해야 합니다.

        - 병원과 돌봄 시설은 충분한가?
        - 청소년과 어린이를 위한 학교·문화시설은 줄어드는가?
        - 일할 수 있는 인구가 줄어들 때 지역 경제는 어떻게 유지될까?
        """
    )

    st.markdown(
        """
        ### 3️⃣ 최근 출생률 반등은 어떻게 볼까?

        최근 한국의 출생률은 오랫동안 낮아지다가 반등 신호가 나타나고 있습니다.  
        하지만 이것을 단순히 “문제가 해결됐다”고 보면 안 됩니다.

        #### ✅ 반등으로 볼 수 있는 이유
        - 혼인 건수 증가
        - 코로나19 이후 미뤄졌던 결혼·출산의 회복
        - 30대 초반 인구집단의 상대적 증가
        - 주거·돌봄·육아 정책 효과 가능성

        #### ⚠️ 조심해야 하는 이유
        - 합계출산율은 여전히 대체출산율 2.1명보다 훨씬 낮음
        - 고용 불안, 주거비, 사교육비, 수도권 집중 문제가 여전히 큼
        - 특정 세대가 출산 연령대에 들어오며 생긴 일시적 효과일 수 있음
        - 지역별 격차가 매우 클 수 있음
        """
    )

    st.markdown(
        """
        ### 4️⃣ 탐구 활동 예시

        #### 🧪 탐구 질문 A
        “우리 지역은 정말 출생 반등이 나타나고 있을까?”

        확인할 지표:
        - 0세 인구와 1세 인구 비교
        - 0세 인구와 1~4세 평균 비교
        - 30~39세 인구 규모
        - 신축 주거지, 전입·전출 자료

        #### 🧪 탐구 질문 B
        “청소년 인구가 줄어들면 학교는 어떻게 달라질까?”

        확인할 지표:
        - 6~18세 인구
        - 초등 연령, 중등 연령, 고등 연령 구분
        - 최근 5년간 학교 수와 학급 수 변화
        - 지역 도서관, 체육시설, 청소년센터 분포
        """
    )

    st.markdown(
        """
        ### 5️⃣ 데이터 윤리

        인구 데이터는 지역을 평가하거나 낙인찍기 위한 도구가 아닙니다.  
        예를 들어 “고령 인구가 많다”는 것은 부정적인 의미만 있는 것이 아닙니다.  
        경험 많은 시민이 많고, 돌봄·의료·평생학습 산업이 성장할 수 있다는 뜻이기도 합니다.

        중요한 것은 데이터를 통해 사람을 단순화하지 않고,  
        **더 좋은 정책과 더 따뜻한 지역사회를 상상하는 것**입니다. 🌱
        """
    )

    st.success(
        """
        🎯 오늘의 핵심  
        인구 데이터 분석은 숫자를 맞히는 활동이 아니라,  
        숫자 뒤에 있는 사람들의 삶과 지역의 미래를 읽는 활동입니다.
        """
    )


# ------------------------------------------------------------
# 9. 푸터
# ------------------------------------------------------------
st.divider()
st.caption(
    "Made with ❤️ Streamlit + Plotly | 데이터 해석 시 주민등록 인구, 출생아 수, 합계출산율은 서로 다른 지표임에 유의하세요."
)
