import streamlit as st
import pandas as pd
import numpy as np
import random
from math import pow

# ----------------------- 리그 시뮬레이션 함수 ----------------------- #
def parse_league_teams(text):
    teams = {}
    lines = text.strip().splitlines()
    for line in lines:
        parts = line.split()
        if len(parts) != 4:
            st.error(f"팀 입력 오류: {line}")
            return None
        name, elo1, elo2, pts = parts
        teams[name] = {
            "기본Elo": float(elo1),
            "최근5경기Elo": float(elo2),
            "승점": int(pts),
            "홈Elo보정": 60
        }
    return teams

def parse_league_matches(text):
    lines = text.strip().splitlines()
    matches = []
    for line in lines:
        parts = line.split()
        if len(parts) != 2:
            st.error(f"경기 입력 오류: {line}")
            return None
        matches.append((parts[0], parts[1]))
    return matches

def win_prob(elo1, elo2):
    diff = (elo2 - elo1) * 1.2
    return 1 / (1 + 10 ** (diff / 400))

def draw_probability(elo1, elo2):
    diff = abs(elo1 - elo2)
    if diff >= 300:
        return 0.15
    elif diff >= 100:
        return 0.18
    else:
        return 0.26 - (diff / 100) * (0.26 - 0.23)

def match_probabilities(team1, team2, teams):
    elo1 = teams[team1]["기본Elo"] * 0.9 + teams[team1]["최근5경기Elo"] * 0.1 + teams[team1].get("홈Elo보정", 0)
    elo2 = teams[team2]["기본Elo"] * 0.9 + teams[team2]["최근5경기Elo"] * 0.1
    base_win = win_prob(elo1, elo2)
    base_lose = 1 - base_win
    draw = draw_probability(elo1, elo2)
    win_adj = pow(base_win, 1)
    lose_adj = pow(base_lose, 1)
    total = win_adj + lose_adj
    win_final = win_adj / total * (1 - draw)
    lose_final = lose_adj / total * (1 - draw)
    return win_final, draw, lose_final

def simulate_match(p1, p_draw, p2):
    r = random.random()
    if r < p1:
        return 3, 0
    elif r < p1 + p_draw:
        return 1, 1
    else:
        return 0, 3

def run_league_sim(teams, matches, n_sim):
    n_teams = len(teams)
    results = {team: {"순위합": 0, "1위횟수": 0, "총승점": 0, "순위별횟수": [0]*n_teams} for team in teams}

    for _ in range(n_sim):
        sim_pts = {team: teams[team]["승점"] for team in teams}
        for team1, team2 in matches:
            p1, p_draw, p2 = match_probabilities(team1, team2, teams)
            s1, s2 = simulate_match(p1, p_draw, p2)
            sim_pts[team1] += s1
            sim_pts[team2] += s2

        ranked = sorted(sim_pts.items(), key=lambda x: x[1], reverse=True)
        for i, (team, pts) in enumerate(ranked):
            results[team]["순위합"] += i + 1
            results[team]["총승점"] += pts
            results[team]["순위별횟수"][i] += 1
        top_pts = ranked[0][1]
        for team, pts in ranked:
            if pts == top_pts:
                results[team]["1위횟수"] += 1
            else:
                break

    table = []
    for team in teams:
        rank_probs = [c / n_sim * 100 for c in results[team]["순위별횟수"]]
        row = {
            "팀명": team,
            "평균순위": results[team]["순위합"] / n_sim,
            "평균승점": results[team]["총승점"] / n_sim,
            "우승확률(%)": results[team]["1위횟수"] / n_sim * 100
        }
        for i, prob in enumerate(rank_probs):
            row[f"{i+1}위 확률(%)"] = prob
        table.append(row)
    return pd.DataFrame(table).sort_values("평균순위")

# ----------------------- Streamlit UI ----------------------- #
st.set_page_config(page_title="축구 시뮬레이터", layout="wide")
st.title("⚽ 축구 리그 시뮬레이터 (모바일 지원)")

with st.expander("1️⃣ 팀 정보 입력 (팀이름 Elo1 Elo2 승점)"):
    team_text = st.text_area("예시: TeamA 1500 1520 3", height=200)

with st.expander("2️⃣ 경기 입력 (팀1 팀2)"):
    match_text = st.text_area("예시: TeamA TeamB", height=200)

col1, col2 = st.columns(2)
with col1:
    n_sim = st.number_input("시뮬레이션 횟수", min_value=100, max_value=100000, value=1000, step=100)
with col2:
    run_button = st.button("시뮬레이션 실행")

if run_button:
    teams = parse_league_teams(team_text)
    matches = parse_league_matches(match_text)
    if teams and matches:
        with st.spinner("시뮬레이션 중..."):
            df = run_league_sim(teams, matches, n_sim)
        st.success("완료!")
        st.dataframe(df, use_container_width=True)
        st.bar_chart(df.set_index("팀명")["우승확률(%)"])
