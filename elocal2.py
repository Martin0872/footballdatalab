import streamlit as st
from collections import defaultdict
from math import sqrt
import re

# -------------------------
# 기본 설정값
# -------------------------
K_VALUE = 20              # Elo 변동 폭
EXPECTED_GOALS = 2.5      # 경기당 기대 득점 (Tilt 계산용)

# -------------------------
# 세션 상태 초기화
# -------------------------
if 'elos' not in st.session_state:
    st.session_state.elos = defaultdict(lambda: 1500.0)
if 'tilts' not in st.session_state:
    st.session_state.tilts = defaultdict(lambda: 1.0)
if 'elo_changes' not in st.session_state:
    st.session_state.elo_changes = []
if 'HFA' not in st.session_state:
    st.session_state.HFA = 42.0

# -------------------------
# 승리 확률 계산
# -------------------------
def expected_score(dr):
    return 1 / (10 ** (-dr / 400) + 1)

# -------------------------
# Elo 업데이트 함수
# -------------------------
def update_elo(home, away, home_goals, away_goals):
    elos = st.session_state.elos
    tilts = st.session_state.tilts
    HFA = st.session_state.HFA
    elo_changes = st.session_state.elo_changes

    home_elo = elos[home] + HFA
    away_elo = elos[away]
    dr = home_elo - away_elo
    expected_home = expected_score(dr)
    result_home = 1 if home_goals > away_goals else 0.5 if home_goals == away_goals else 0

    margin = abs(home_goals - away_goals) or 1
    base_change = (result_home - expected_home) * K_VALUE
    margin_adj = base_change * sqrt(margin)

    elos[home] += margin_adj
    elos[away] -= margin_adj
    elo_changes.append((home, away, margin_adj))

    # Tilt 업데이트
    total_goals = home_goals + away_goals
    tilt_home_old = tilts[home]
    tilt_away_old = tilts[away]
    tilts[home] = 0.98 * tilt_home_old + 0.02 * (total_goals / tilt_away_old / EXPECTED_GOALS)
    tilts[away] = 0.98 * tilt_away_old + 0.02 * (total_goals / tilt_home_old / EXPECTED_GOALS)

    # HFA 자동 보정
    if len(elo_changes) >= 10:
        net_home_gain = sum([delta for h, a, delta in elo_changes if h == home])
        net_away_gain = sum([-delta for h, a, delta in elo_changes if a == away])
        st.session_state.HFA += (net_home_gain - net_away_gain) * 0.075
        st.session_state.elo_changes = []

# -------------------------
# UI
# -------------------------
stitle = "Elo 계산기"
st.title(stitle)

# 초기 Elo 입력
initial_input = st.text_area(
    "초기 Elo 입력 (팀이름 Elo값, 한 줄에 하나씩)", height=150, key="initial_input"
)
if st.button("초기 Elo 설정"):
    lines = initial_input.strip().splitlines()
    for line in lines:
        parts = line.strip().split()
        if len(parts) < 2:
            st.error(f"형식 오류: {line}")
            continue
        team = " ".join(parts[:-1])
        try:
            value = float(parts[-1])
        except ValueError:
            st.error(f"Elo값 오류: {line}")
            continue
        st.session_state.elos[team] = value
    st.success("초기 Elo 설정 완료.")

# 경기 결과 입력
result_input = st.text_area(
    "경기 결과 입력 (홈팀 2-1 원정팀, 한 줄에 하나씩)", height=150, key="result_input"
)
if st.button("결과 입력"):
    lines = result_input.strip().splitlines()
    for line in lines:
        match = re.match(r"(.+?) (\d+)-(\d+) (.+)", line)
        if not match:
            st.error(f"형식 오류: {line}")
            continue
        home, hg, ag, away = match.groups()
        update_elo(home.strip(), away.strip(), int(hg), int(ag))
    st.session_state.result_input = ""
    st.success("결과 반영 완료.")

# Elo 출력
st.subheader(f"현재 HFA: {st.session_state.HFA:.2f}")

# 정렬된 팀 리스트
sorted_data = sorted(
    st.session_state.elos.items(), key=lambda x: -x[1]
)
rows = []
for team, elo in sorted_data:
    tilt = st.session_state.tilts[team]
    rows.append({"팀": team, "Elo": f"{elo:.1f}", "Tilt": f"{tilt:.3f}"})

st.table(rows)
