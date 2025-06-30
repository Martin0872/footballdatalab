import streamlit as st
import pandas as pd
import random
from math import pow

# --- Simulation functions ---
def parse_teams(input_text):
    teams = {}
    lines = input_text.strip().splitlines()
    for line in lines:
        parts = line.split()
        if len(parts) != 3:
            st.error(f"팀 입력 형식 오류: '{line}' (팀이름 현재Elo 현재승점)")
            st.stop()
        name, elo, points = parts[0], parts[1], parts[2]
        try:
            elo = float(elo)
            points = int(points)
        except ValueError:
            st.error(f"숫자 변환 오류: '{line}'")
            st.stop()
        teams[name] = {"Elo": elo, "승점": points, "홈Elo보정": 60}
    return teams


def parse_matches(input_text, teams):
    matches = []
    lines = input_text.strip().splitlines()
    names = set(teams.keys())
    for line in lines:
        parts = line.split()
        if len(parts) != 2:
            st.error(f"경기 입력 형식 오류: '{line}'")
            st.stop()
        t1, t2 = parts
        if t1 not in names or t2 not in names:
            st.error(f"팀 이름 오류: '{t1}' 또는 '{t2}'")
            st.stop()
        matches.append((t1, t2))
    return matches


def combined_elo(team, teams, is_home=False):
    base = teams[team]["Elo"]
    return base + teams[team].get("홈Elo보정", 0) if is_home else base


def win_prob(e1, e2):
    diff = (e2 - e1) * 1.2
    return 1 / (1 + 10 ** (diff / 400))


def draw_probability(e1, e2):
    diff = abs(e1 - e2)
    if diff >= 300:
        return 0.15
    elif diff >= 100:
        return 0.18
    else:
        return 0.26 - (diff / 100) * (0.26 - 0.23)


def match_probabilities(t1, t2, teams, p=1):
    e1 = combined_elo(t1, teams, True)
    e2 = combined_elo(t2, teams, False)
    b1 = win_prob(e1, e2)
    b2 = 1 - b1
    d = draw_probability(e1, e2)
    w = pow(b1, p)
    l = pow(b2, 1/p)
    total = w + l
    w /= total; l /= total
    w *= (1 - d); l *= (1 - d)
    return w, d, l


def simulate_match(p1, pd, p2):
    r = random.random()
    if r < p1:
        return 3, 0
    elif r < p1 + pd:
        return 1, 1
    else:
        return 0, 3


def run_simulation(teams, matches, n_sim):
    n = len(teams)
    results = {t: {"sum_rank":0, "win1":0, "sum_pts":0, "rank_counts":[0]*n} for t in teams}
    for _ in range(n_sim):
        pts = {t: teams[t]["승점"] for t in teams}
        for t1, t2 in matches:
            p1, pd, p2 = match_probabilities(t1, t2, teams)
            s1, s2 = simulate_match(p1, pd, p2)
            pts[t1] += s1; pts[t2] += s2
        sorted_pts = sorted(pts.items(), key=lambda x: x[1], reverse=True)
        max_pt = sorted_pts[0][1]
        for rank, (t, p) in enumerate(sorted_pts,1):
            results[t]["sum_rank"] += rank
            results[t]["sum_pts"] += p
            results[t]["rank_counts"][rank-1] += 1
            if p == max_pt:
                results[t]["win1"] += 1
    summary = []
    for t,data in results.items():
        probs = [c/n_sim*100 for c in data["rank_counts"]]
        summary.append({
            "팀": t,
            "평균승점": data["sum_pts"]/n_sim,
            **{f"{i}위확률(%)": probs[i-1] for i in range(1,n+1)},
            "우승확률(%)": data["win1"]/n_sim*100
        })
    return pd.DataFrame(summary).sort_values("평균승점", ascending=False)

# --- Streamlit UI ---
st.title("축구 경기 시뮬레이션 (Streamlit)")

st.sidebar.header("입력 설정")
team_input = st.sidebar.text_area("팀 정보 (팀이름 Elo 승점)", height=200, value="팀A 1500 0\n팀B 1500 0")
match_input = st.sidebar.text_area("경기 리스트 (팀1 팀2)", height=200, value="팀A 팀B")
n_sim = st.sidebar.number_input("시뮬레이션 횟수", min_value=1, value=1000)
range_str = st.sidebar.text_input("확률 범위 (예: 3~6)", value="1~2")
run = st.sidebar.button("시뮬레이션 실행")

if run:
    teams = parse_teams(team_input)
    matches = parse_matches(match_input, teams)
    df_summary = run_simulation(teams, matches, int(n_sim))
    # 전체 요약
    st.subheader("시뮬레이션 결과 요약")
    st.dataframe(df_summary)
    # 범위 확률
    try:
        start, end = map(int, range_str.split("~"))
        if not (1 <= start <= end <= len(teams)):
            raise ValueError
        df_summary[f"{start}~{end}위확률(%)"] = df_summary[[f"{i}위확률(%)" for i in range(start, end+1)]].sum(axis=1)
        st.subheader(f"{start}~{end}위 확률")
        st.dataframe(df_summary[["팀", f"{start}~{end}위확률(%)"]])
    except:
        st.warning("범위 입력을 확인하세요. 예: 3~6")
    # 개별 경기 확률
    st.subheader("매치별 승무패 확률")
    mp = []
    for t1,t2 in matches:
        w,d,l = match_probabilities(t1,t2,teams)
        mp.append({"경기":f"{t1} vs {t2}","승리(%)":w*100,"무(%)":d*100,"패배(%)":l*100})
    st.dataframe(pd.DataFrame(mp))
