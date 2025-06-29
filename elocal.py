import streamlit as st
import re
from collections import defaultdict
import pandas as pd

# 세션 스테이트에 Elo 저장용
if 'elos' not in st.session_state:
    st.session_state.elos = defaultdict(lambda: 1500)

# Elo 계산 함수
@st.cache_data
def calculate_elo(R_a, R_b, result_a, is_home_a=True, K=40):
    H = (R_a * 0.025 + 3) if is_home_a else 0
    expected_a = 1 / (1 + 10 ** ((R_b - R_a + H) / 400))
    expected_b = 1 - expected_a
    R_a_new = R_a + K * (result_a - expected_a)
    R_b_new = R_b + K * ((1 - result_a) - expected_b)
    return round(R_a_new, 1), round(R_b_new, 1)

# 경기 결과 파싱
def parse_match(result_str):
    match = re.match(r"(.+?) (\d+)-(\d+) (.+)", result_str.strip())
    if not match:
        raise ValueError("형식 오류: '홈팀 스코어-스코어 원정팀' 형태로 입력해주세요.")
    team_a, score_a, score_b, team_b = match.groups()
    return team_a.strip(), int(score_a), int(score_b), team_b.strip()

st.title("Elo 점수 계산기")
st.write("기본 Elo 점수는 1500입니다.")

# 초기 Elo 입력
initial_input = st.text_area("초기 Elo 입력 (예: 천안 1530)", height=150)
if st.button("초기 Elo 설정"):
    try:
        for line in initial_input.splitlines():
            if not line.strip():
                continue
            team, rating = line.rsplit(" ", 1)
            st.session_state.elos[team.strip()] = float(rating)
        st.success("초기 Elo 설정 완료.")
    except Exception as e:
        st.error(f"초기 Elo 형식 오류: {e}")

# 경기 결과 입력 및 반영
match_input = st.text_area("여러 경기 결과 입력 (예: 천안 0-2 전남)", height=200)
if st.button("경기 반영"):
    try:
        for line in match_input.splitlines():
            if not line.strip():
                continue
            team_a, score_a, score_b, team_b = parse_match(line)
            # 결과 판정
            if score_a > score_b:
                result = 1
            elif score_a < score_b:
                result = 0
            else:
                result = 0.5
            # 기존 Elo 가져오기 (기본값 1500)
            R_a = st.session_state.elos[team_a]
            R_b = st.session_state.elos[team_b]
            # 새로운 Elo 계산
            new_Ra, new_Rb = calculate_elo(R_a, R_b, result, is_home_a=True)
            st.session_state.elos[team_a] = new_Ra
            st.session_state.elos[team_b] = new_Rb
        st.success("경기 반영 완료.")
    except ValueError as ve:
        st.error(str(ve))
    except KeyError as ke:
        st.error(f"팀 '{ke.args[0]}'의 Elo 점수가 설정되지 않았습니다.")

# 현재 Elo 테이블 출력
df = pd.DataFrame(list(st.session_state.elos.items()), columns=["팀", "Elo"] )
df = df.sort_values(by="Elo", ascending=False).reset_index(drop=True)
st.dataframe(df)
