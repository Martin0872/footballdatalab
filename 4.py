import streamlit as st
import re
from collections import defaultdict
from math import sqrt

# --- Session State Initialization ---
if 'elos' not in st.session_state:
    st.session_state.elos = defaultdict(lambda: 1500.0)
if 'tilts' not in st.session_state:
    st.session_state.tilts = defaultdict(lambda: 1.0)
if 'elo_changes' not in st.session_state:
    st.session_state.elo_changes = []
if 'HFA' not in st.session_state:
    st.session_state.HFA = 42.0

# --- Constants ---
K_VALUE = 20              # Elo 변동 폭 (장기 안정형)
EXPECTED_GOALS = 2.5      # 경기당 기대 득점 (Tilt 계산용)

# --- Helper Functions ---
def expected_score(dr):
    return 1 / (10 ** (-dr / 400) + 1)


def update_elo(home, away, home_goals, away_goals):
    elos = st.session_state.elos
    tilts = st.session_state.tilts
    changes = st.session_state.elo_changes
    HFA = st.session_state.HFA

    home_elo = elos[home] + HFA
    away_elo = elos[away]
    dr = home_elo - away_elo
    exp_home = expected_score(dr)
    res_home = 1 if home_goals > away_goals else 0.5 if home_goals == away_goals else 0

    margin = max(abs(home_goals - away_goals), 1)
    base_change = (res_home - exp_home) * K_VALUE
    margin_adj = base_change * sqrt(margin)

    elos[home] += margin_adj
    elos[away] -= margin_adj
    changes.append((home, away, margin_adj))

    # Tilt 업데이트
    total_goals = home_goals + away_goals
    old_home_tilt = tilts[home]
    old_away_tilt = tilts[away]
    tilts[home] = 0.98 * old_home_tilt + 0.02 * (total_goals / old_away_tilt / EXPECTED_GOALS)
    tilts[away] = 0.98 * old_away_tilt + 0.02 * (total_goals / old_home_tilt / EXPECTED_GOALS)

    # HFA 자동 보정
    if len(changes) >= 10:
        net_home_gain = sum(delta for h, a, delta in changes)
        net_away_gain = -sum(delta for h, a, delta in changes)
        st.session_state.HFA = HFA + (net_home_gain - net_away_gain) * 0.075
        changes.clear()


def show_elo():
    elos = st.session_state.elos
    tilts = st.session_state.tilts
    HFA = st.session_state.HFA
    sorted_list = sorted(elos.items(), key=lambda x: -x[1])
    st.write(f"**[HFA 현재값: {HFA:.2f}]**")
    for team, elo in sorted_list:
        st.write(f"- {team}: Elo {elo:.1f} / Tilt {tilts[team]:.3f}")

# --- Streamlit UI ---
st.set_page_config(page_title="Elo Calculator Streamlit", layout="centered")
st.title("Elo Calculator with Streamlit")

with st.expander("초기 Elo 입력 (팀이름 Elo값)", expanded=True):
    initial_input = st.text_area("한 줄당 팀과 Elo 입력 (예: Arsenal 1500)")
    if st.button("초기화 설정", key="init_elo"):
        lines = initial_input.strip().splitlines()
        for line in lines:
            parts = line.strip().split()
            if len(parts) < 2:
                st.error(f"Elo 형식 오류: {line}")
                continue
            team = " ".join(parts[:-1])
            try:
                val = float(parts[-1])
            except ValueError:
                st.error(f"숫자 변환 오류: {line}")
                continue
            st.session_state.elos[team] = val
        # 버튼 클릭으로 인해 자동 rerun

with st.expander("경기 결과 입력 (홈팀 2-1 원정팀)", expanded=True):
    result_input = st.text_area("한 줄당 경기 결과 입력 (예: Arsenal 2-1 Chelsea)")
    if st.button("결과 처리", key="process_res"):
        lines = result_input.strip().splitlines()
        for line in lines:
            m = re.match(r"(.+?) (\d+)-(\d+) (.+)", line)
            if not m:
                st.error(f"형식 오류: {line}")
                continue
            home, hg, ag, away = m.groups()
            update_elo(home.strip(), away.strip(), int(hg), int(ag))
        # 버튼 클릭으로 인해 자동 rerun

st.subheader("현재 Elo & Tilt")
show_elo()
