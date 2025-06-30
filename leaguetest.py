import streamlit as st
import random
from math import pow

# -------------------------
# 함수 정의
# -------------------------
def parse_teams(input_text):
    teams = {}
    for line in input_text.strip().splitlines():
        parts = line.split()
        if len(parts) != 3:
            st.error(f"팀 입력 형식 오류: '{line}' (팀이름 현재Elo 현재승점)")
            return None
        name, elo_str, pts_str = parts
        try:
            elo = float(elo_str)
            pts = int(pts_str)
        except ValueError:
            st.error(f"숫자 변환 오류: '{line}'")
            return None
        teams[name] = {"Elo": elo, "승점": pts, "홈Elo보정": 60}
    return teams


def parse_matches(input_text, teams):
    matches = []
    team_names = set(teams.keys())
    for line in input_text.strip().splitlines():
        parts = line.split()
        if len(parts) != 2:
            st.error(f"경기 입력 형식 오류: '{line}' (팀1 팀2)")
            return None
        t1, t2 = parts
        if t1 not in team_names or t2 not in team_names:
            st.error(f"팀 이름 오류: '{t1}' 또는 '{t2}'가 미등록 팀입니다.")
            return None
        matches.append((t1, t2))
    return matches


def combined_elo(team, teams, is_home=False):
    base = teams[team]["Elo"]
    return base + (teams[team].get("홈Elo보정", 0) if is_home else 0)


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
    wp = win_prob(e1, e2)
    lp = 1 - wp
    dp = draw_probability(e1, e2)
    adj_w = pow(wp, p)
    adj_l = pow(lp, 1/p)
    total = adj_w + adj_l
    w_final = adj_w / total * (1 - dp)
    l_final = adj_l / total * (1 - dp)
    return w_final, dp, l_final


def simulate_match(pw, pd, pl):
    r = random.random()
    if r < pw:
        return 3, 0
    elif r < pw + pd:
        return 1, 1
    else:
        return 0, 3


def run_simulation(teams, matches, n_sim):
    n = len(teams)
    res = {t: {"순위합":0, "1위횟수":0, "총승점":0, "순위별횟수":[0]*n} for t in teams}
    for _ in range(n_sim):
        pts = {t: teams[t]["승점"] for t in teams}
        for t1, t2 in matches:
            pw, pd, pl = match_probabilities(t1, t2, teams)
            s1, s2 = simulate_match(pw, pd, pl)
            pts[t1] += s1; pts[t2] += s2
        sorted_pts = sorted(pts.items(), key=lambda x: x[1], reverse=True)
        top = sorted_pts[0][1]
        for rank, (t, p) in enumerate(sorted_pts,1):
            res[t]["순위합"] += rank
            res[t]["총승점"] += p
            res[t]["순위별횟수"][rank-1] += 1
            if p == top:
                res[t]["1위횟수"] += 1
            else:
                break
    summs = {}
    for t in teams:
        cnt = float(n_sim)
        probs = [c/cnt*100 for c in res[t]["순위별횟수"]]
        summs[t] = {"평균승점":res[t]["총승점"]/cnt, **{f"{i}위 확률(%)":probs[i-1] for i in range(1,n+1)}}
    return summs

# -------------------------
# Streamlit UI
# -------------------------
st.title("축구 경기 시뮬레이션")
teams_input = st.text_area("팀 정보 입력 (팀이름 현재Elo 현재승점)", height=150)
matches_input = st.text_area("경기 입력 (팀1 팀2)", height=150)
sim_count = st.number_input("시뮬레이션 횟수", min_value=1, value=1000, step=1)
prob_range = st.text_input("확률 범위 (예: 3~6)", value="3~6")

if st.button("시뮬레이션 실행"):
    teams = parse_teams(teams_input)
    matches = parse_matches(matches_input, teams) if teams else None
    if not teams or not matches:
        st.stop()
    try:
        n1, n2 = map(int, prob_range.split("~"))
    except:
        st.error("확률 범위 형식 오류: 예 '3~6'")
        st.stop()
    summary = run_simulation(teams, matches, sim_count)
    # 리그 결과
    table = []
    for t, data in sorted(summary.items(), key=lambda x: x[1]["평균승점"], reverse=True):
        row = {"팀명": t, "평균승점": f"{data['평균승점']:.2f}"}
        probs = [float(data[f"{i}위 확률(%)"]) for i in range(1, len(teams)+1)]
        for i, p in enumerate(probs,1): row[f"{i}위 확률(%)"] = f"{p:.2f}"
        row[f"{n1}~{n2}위 확률(%)"] = f"{sum(probs[n1-1:n2]):.2f}"
        table.append(row)
    st.subheader("시뮬레이션 결과")
    st.table(table)
    # 경기별 확률
    st.subheader("경기별 승무패 확률")
    match_table = []
    for t1, t2 in matches:
        w,d,l = match_probabilities(t1, t2, teams)
        match_table.append({"경기":f"{t1} vs {t2}", "승리 확률(%)":f"{w*100:.2f}", "무승부 확률(%)":f"{d*100:.2f}", "패배 확률(%)":f"{l*100:.2f}"})
    st.table(match_table)
