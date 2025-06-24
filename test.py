import streamlit as st
import pandas as pd
import numpy as np
import random
from math import pow
import re

st.set_page_config(page_title="축구 시뮬레이터", layout="wide")
st.title("⚽ 축구 시뮬레이터 (리그 & 조별리그)")

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

# ----------------------- 조별리그 함수 ----------------------- #
def parse_group_teams(text):
    teams = {}
    for line in text.strip().splitlines():
        name, elo1, elo2, pts = line.split()
        teams[name] = {"elo1": float(elo1), "elo2": float(elo2), "pts": int(pts)}
    return teams

def parse_group_matches(text):
    return [tuple(line.split()) for line in text.strip().splitlines() if line.strip()]

def parse_group_results(text):
    results = []
    pattern = re.compile(r"(\S+) (\d+)-(\d+) (\S+)")
    for line in text.strip().splitlines():
        m = pattern.match(line)
        if m:
            t1, g1, g2, t2 = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
            results.append((t1, t2, g1, g2))
    return results

def run_group_sim(teams, matches, past_results, n_sim, rank_start, rank_end):
    counts = {t: [0] * len(teams) for t in teams}
    for _ in range(n_sim):
        results = list(past_results)
        for t1, t2 in matches:
            elo1 = teams[t1]['elo1'] * 0.9 + teams[t1]['elo2'] * 0.1
            elo2 = teams[t2]['elo1'] * 0.9 + teams[t2]['elo2'] * 0.1
            wp, dp, lp = match_probabilities(t1, t2, teams)
            s1, s2 = simulate_match(wp, dp, lp)
            results.append((t1, t2, s1, s2))
        stats = {t: {"pts": teams[t]['pts'], "gf": 0, "ga": 0} for t in teams}
        for t1, t2, g1, g2 in results:
            stats[t1]["gf"] += g1
            stats[t1]["ga"] += g2
            stats[t2]["gf"] += g2
            stats[t2]["ga"] += g1
            if g1 > g2:
                stats[t1]["pts"] += 3
            elif g1 < g2:
                stats[t2]["pts"] += 3
            else:
                stats[t1]["pts"] += 1
                stats[t2]["pts"] += 1
        ranking = sorted(teams.keys(), key=lambda t: (stats[t]["pts"], stats[t]["gf"] - stats[t]["ga"], stats[t]["gf"]), reverse=True)
        for i, t in enumerate(ranking):
            counts[t][i] += 1
    rows = []
    for t in teams:
        probs = [c / n_sim * 100 for c in counts[t]]
        range_prob = sum(probs[rank_start-1:rank_end])
        row = {"팀명": t, **{f"{i+1}위": f"{p:.1f}%" for i, p in enumerate(probs)}, f"{rank_start}~{rank_end}위": f"{range_prob:.1f}%"}
        rows.append(row)
    return pd.DataFrame(rows)

# ----------------------- Streamlit UI ----------------------- #
tabs = st.tabs(["🏆 리그 시뮬레이션", "🏟 조별리그 시뮬레이션"])

with tabs[0]:
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

with tabs[1]:
    st.markdown("### 🏟 조별리그 시뮬레이션")
    t_input = st.text_area("1️⃣ 팀 입력 (팀 Elo1 Elo2 승점)", height=150)
    m_input = st.text_area("2️⃣ 예정 경기 입력 (팀1 팀2)", height=100)
    r_input = st.text_area("3️⃣ 이전 경기 결과 입력 (팀1 점수-점수 팀2)", height=100)
    col1, col2, col3 = st.columns(3)
    with col1:
        g_sim = st.number_input("시뮬레이션 횟수", value=1000, step=500)
    with col2:
        r_start = st.number_input("순위 구간 시작", value=1, step=1)
    with col3:
        r_end = st.number_input("순위 구간 끝", value=2, step=1)
    if st.button("조별리그 시뮬레이션 실행"):
        try:
            teams = parse_group_teams(t_input)
            matches = parse_group_matches(m_input)
            past = parse_group_results(r_input)
            with st.spinner("시뮬레이션 중..."):
                df = run_group_sim(teams, matches, past, g_sim, r_start, r_end)
            st.success("완료!")
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"입력 오류: {e}")
