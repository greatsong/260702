import streamlit as st
import random

# 1. 페이지 기본 설정 및 타이틀
st.set_page_config(page_title="MBTI 포켓몬 & 직업 추천", page_icon="🔮", layout="centered")

st.title("🔮 MBTI 포켓몬 & 직업 매칭 연구소 🧪")
st.markdown("---")

# 2. MBTI 데이터베이스 정의 (포켓몬 이미지 ID 및 추천 직업)
mbti_db = {
    "ISTJ": {"pokemon_id": 9, "pokemon_name": "거북왕", "jobs": ["📊 데이터 분석가", "⚖️ 준법 감시인", "🏢 행정 관리자"], "effect": "balloons"},
    "ISFJ": {"pokemon_id": 1, "pokemon_name": "이상해씨", "jobs": ["🏥 간호사/의료인", "🏫 초등 교사", "🛡️ 사회복지사"], "effect": "snow"},
    "INFJ": {"pokemon_id": 151, "pokemon_name": "뮤", "jobs": ["🧠 상담 심리사", "✍️ 작가/시인", "🎨 환경 디자이너"], "effect": "balloons"},
    "INTJ": {"pokemon_id": 150, "pokemon_name": "뮤츠", "jobs": ["💻 소프트웨어 아키텍트", "📈 전략 기획자", "🔬 연구원"], "effect": "balloons"},
    "ISTP": {"pokemon_id": 4, "pokemon_name": "파이리", "jobs": ["⚙️ 엔지니어", "🕵️ forensic 전문가", "🏎️ 파일럿/카레이서"], "effect": "snow"},
    "ISFP": {"pokemon_id": 25, "pokemon_name": "피카츄", "jobs": ["🎨 일러스트레이터", "🎵 뮤지션", "💐 플로리스트"], "effect": "snow"},
    "INFP": {"pokemon_id": 133, "pokemon_name": "이브이", "jobs": ["📝 카피라이터", "🎨 예술 치료사", " HRD 교육 전문가"], "effect": "snow"},
    "INTP": {"pokemon_id": 65, "pokemon_name": "후딘", "jobs": ["🖥️ AI 연구원", "📐 경제학자", "🔓 정보보안 전문가"], "effect": "balloons"},
    "ESTP": {"pokemon_id": 6, "pokemon_name": "리자몽", "jobs": ["💼 사업가", "🎤 마케터", "🚒 소방관/경찰관"], "effect": "balloons"},
    "ESFP": {"pokemon_id": 39, "pokemon_name": "푸린", "jobs": ["🎬 연예인/배우", "✈️ 승무원", "🎉 이벤트 플래너"], "effect": "snow"},
    "ENFP": {"pokemon_id": 149, "pokemon_name": "망나뇽", "jobs": ["💡 크리에이티브 디렉터", "📣 홍보 전문가", "🌍 여행가"], "effect": "balloons"},
    "ENTP": {"pokemon_id": 94, "pokemon_name": "팬텀", "jobs": ["🚀 스타트업 창업가", "🧑‍⚖️ 변호사", " 컨설턴트"], "effect": "balloons"},
    "ESTJ": {"pokemon_id": 68, "pokemon_name": "괴력몬", "jobs": ["👔 경영 실무자", "📈 프로젝트 매니저", "🏦 자산 관리사"], "effect": "balloons"},
    "ESFJ": {"pokemon_id": 35, "pokemon_name": "삐삐", "jobs": ["🤝 인사(HR) 담당자", "🏨 호텔리어", "🏫 상담 교사"], "effect": "snow"},
    "ENFJ": {"pokemon_id": 249, "pokemon_name": "루기아", "jobs": ["정치/사회적 리더", "📢 비영리단체 운영자", "🧑‍🏫 교육 컨설턴트"], "effect": "balloons"},
    "ENTJ": {"pokemon_id": 130, "pokemon_name": "갸라도스", "jobs": ["CEO / 최고 경영자", " 경영 컨설턴트", "벤처 캐피탈리스트"], "effect": "balloons"}
}

# 3. 사이드바 또는 메인 화면에서 MBTI 선택
st.subheader("나의 MBTI 성향은 무엇인가요? 🤔")
mbti_list = sorted(list(mbti_db.keys()))
selected_mbti = st.selectbox("아래 목록에서 선택해보세요 ✨", mbti_list, index=None, placeholder="MBTI 선택하기...")

# 4. 결과 출력 및 특수 효과
if selected_mbti:
    data = mbti_db[selected_mbti]
    
    # 팡팡 터지는 시각 효과 제어
    if data["effect"] == "balloons":
        st.balloons()
    else:
        st.snow()
        
    st.markdown("---")
    
    # 결과 레이아웃 구성 (2단 컬럼 구조)
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        st.success(f"### 🎉 당신의 매칭 결과: {selected_mbti}")
        st.metric(label="동반자 포켓몬", value=data["pokemon_name"])
        
        # PokeAPI의 공식 고화질 일러스트레이션 URL 사용
        image_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{data['pokemon_id']}.png"
        st.image(image_url, use_container_width=True)
        
    with col2:
        st.info("### 💼 가장 잘 어울리는 직업 TOP 3")
        st.write("당신의 성향에 잠재된 능력을 발휘할 수 있는 직업군입니다:")
        
        # 가독성을 높이기 위한 예쁜 마크다운 리스트 효과
        for i, job in enumerate(data["jobs"], 1):
            st.markdown(f"#### {i}. {job}")
            
        # 소소한 재미를 주는 랜덤 응원 한마디
        cheers = [
            "당신의 숨겨진 잠재력은 포켓몬처럼 진화할 준비가 되어 있어요! 💪",
            "이 직업군에서 당신은 최고의 마스터가 될 수 있습니다! 🔥",
            "당신만의 특별한 특성(Ability)을 세상에 보여주세요! 🌟"
        ]
        st.warning(f"💡 **한 줄 조언:** {random.choice(cheers)}")

else:
    # 아무것도 선택되지 않았을 때의 안내 문구
    st.light_sidebar = True
    st.info("👆 위 드롭다운 메뉴에서 MBTI를 선택하면 어울리는 포켓몬과 직업이 나타납니다!")
