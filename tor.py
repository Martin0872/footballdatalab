import streamlit as st
import pandas as pd
import random
from collections import defaultdict

# Elo 기반 승률 계산

def elo_win_prob(elo_A: int, elo_B: int, k: int = 400) -> float:
    return 1 / (1 + 10 ** (-(elo_A - elo_B) / k))

# 단일 경기 시뮬레이션

def simulate_match(elo_A: int, elo_B: int, draw_rate: float = 0.24) -> str:
    P = elo_win_prob(elo_A, elo_B)
    p_draw = draw_rate
    p_A_win = P - p_draw / 2
    r = random.random()
    if r < p_A_win:
        return "A"
    elif r < p_A_win + p_draw:
        # 무승부 시 랜덤 결정
        return "A" if random.random() < 0.5 else "B"
    else:
        return "B"

# 입력 문자열을 번호별 매치맵으로 파싱

def parse_team_input(raw_text: str):
    matches = defaultdict(list)
    for line in raw_text.strip().splitlines():
        parts = line.split()
        if len(parts) != 3:
            st.error(f"팀 입력 형식 오류: '{line}' (번호 이름 Elo)")
            return None
        try:
            num = int(parts[0])
            name = parts[1]
            elo = int(parts[2])
        except ValueError:
            st.error(f"숫자 변환 오류: '{line}'")
            return None
        matches[num].append((name, elo))
    return matches

# 한 라운드의 승자들 다음 라운드 구성

def simulate_round(round_matches: dict):
    next_round = {}
    champion = None
    keys = sorted(round_matches.keys())

    # 최종 결승
    if len(keys) == 1:
        m = round_matches[keys[0]]
        if len(m) == 2:
            win = simulate_match(m[0][1], m[1][1])
            champion = m[0][0] if win == "A" else m[1][0]
        return {}, champion

    # 그 외 라운드
    for i in range(0, len(keys), 2):
        if i + 1 >= len(keys):
            break
        m1 = round_matches[keys[i]]
        m2 = round_matches[keys[i+1]]
        if len(m1) < 2 or len(m2) < 2:
            continue
        win1 = simulate_match(m1[0][1], m1[1][1])
        winner1 = m1[0] if win1 == "A" else m1[1]
        win2 = simulate_match(m2[0][1], m2[1][1])
        winner2 = m2[0] if win2 == "A" else m2[1]
        next_num = i // 2 + 1
        next_round[next_num] = [winner1, winner2]

    return next_round, champion

# 전체 시뮬레이션

def run_simulations(raw_text: str, start_round: str, n_sim: int) -> pd.DataFrame:
    order = ["16강", "8강", "4강", "결승"]
    advance = {"16강": "8강", "8강": "4강", "4강": "결승", "결승": "우승"}
    start_idx = order.index(start_round)
    rounds = order[start_idx:]

    counts = defaultdict(lambda: defaultdict(int))

    for _ in range(n_sim):
        matches = parse_team_input(raw_text)
        if matches is None:
            return None
        for r in rounds:
            matches, champ = simulate_round(matches)
            if r != "결승":
                for pair in matches.values():
                    for team, _ in pair:
                        counts[team][advance[r]] += 1
            else:
                if champ:
                    counts[champ]["우승"] += 1
    # 결과 DataFrame
    df = pd.DataFrame(counts).T.fillna(0)
    cols = [advance[r] for r in rounds if r != "결승"] + ["우승"]
    df = df[[c for c in cols if c in df.columns]]
    df = df.applymap(lambda x: round(100 * x / n_sim, 2))
    df.index.name = "팀"
    return df.reset_index()

# Streamlit UI
st.title("토너먼트 시뮬레이터")
start = st.selectbox("시작 라운드", ["16강", "8강", "4강", "결승"], index=0)
n = st.number_input("시뮬레이션 횟수", min_value=1, value=10000, step=1000)
raw = st.text_area("팀 입력 (번호 이름 Elo)", height=200)

if st.button("시뮬레이션 시작"):
    result = run_simulations(raw, start_round=start, n_sim=n)
    if result is not None:
        st.dataframe(result)
    else:
        st.error("입력 형식 오류가 발생했습니다.")
