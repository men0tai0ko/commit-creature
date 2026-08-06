#!/usr/bin/env python3
"""コミット生物: リポジトリの活動を集計し、生物の状態(data/creature.json)と
見た目(docs/creature.svg)を更新するスクリプト。GitHub Actionsから毎日実行される。
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "creature.json"
SVG_PATH = ROOT / "docs" / "creature.svg"
STATUS_PATH = ROOT / "docs" / "status.json"

STAGES = [
    {"name": "たまご", "key": "egg", "min_exp": 0},
    {"name": "幼体", "key": "hatchling", "min_exp": 10},
    {"name": "成体", "key": "adult", "min_exp": 30},
    {"name": "進化体", "key": "evolved", "min_exp": 70},
    {"name": "伝説体", "key": "legendary", "min_exp": 150},
]

COMMIT_POINTS = 2
PR_POINTS = 5
ISSUE_POINTS = 3
HUNGRY_PENALTY = -1
HISTORY_LIMIT = 30


def count_recent_commits(since="24.hours.ago") -> int:
    try:
        out = subprocess.run(
            ["git", "log", f"--since={since}", "--oneline"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        lines = [l for l in out.stdout.splitlines() if l.strip()]
        return len(lines)
    except Exception:
        return 0


def github_api_get(path: str):
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not repo:
        return None
    url = f"https://api.github.com/repos/{repo}{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError):
        return None


def count_recent_prs_and_issues(since_dt: datetime) -> tuple[int, int]:
    merged_prs = 0
    closed_issues = 0
    items = github_api_get("/issues?state=closed&per_page=50")
    if not items:
        return merged_prs, closed_issues
    for item in items:
        closed_at = item.get("closed_at")
        if not closed_at:
            continue
        closed_time = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
        if closed_time < since_dt:
            continue
        if "pull_request" in item:
            if item.get("pull_request", {}).get("merged_at"):
                merged_prs += 1
        else:
            closed_issues += 1
    return merged_prs, closed_issues


def load_state() -> dict:
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {
        "exp": 0,
        "stage_index": 0,
        "mood": "sleepy",
        "history": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_run": None,
    }


def stage_for_exp(exp: int) -> int:
    idx = 0
    for i, s in enumerate(STAGES):
        if exp >= s["min_exp"]:
            idx = i
    return idx


def mood_for_score(score: int) -> str:
    if score >= 5:
        return "great"
    if score > 0:
        return "good"
    if score == 0:
        return "neutral"
    return "hungry"


PALETTE = {
    "great": {"body": "#ffd166", "cheek": "#ff6b6b"},
    "good": {"body": "#8be0b0", "cheek": "#ff8fa3"},
    "neutral": {"body": "#a0c4ff", "cheek": "#ffd6a5"},
    "hungry": {"body": "#c9c9c9", "cheek": "#e0aaff"},
}


def render_svg(stage_index: int, mood: str, exp: int) -> str:
    stage = STAGES[stage_index]
    colors = PALETTE.get(mood, PALETTE["neutral"])
    body_color = colors["body"]
    cheek_color = colors["cheek"]

    size = 60 + stage_index * 18
    cx, cy = 150, 160
    eye_offset = size * 0.32
    eye_r = 6 + stage_index * 0.6

    # 表情: hungryは半目、great/goodは笑顔、neutralは普通
    if mood == "hungry":
        mouth = f'<path d="M {cx-14} {cy+size*0.35} Q {cx} {cy+size*0.25} {cx+14} {cy+size*0.35}" stroke="#555" stroke-width="3" fill="none" stroke-linecap="round"/>'
    elif mood in ("great", "good"):
        mouth = f'<path d="M {cx-16} {cy+size*0.3} Q {cx} {cy+size*0.55} {cx+16} {cy+size*0.3}" stroke="#555" stroke-width="3" fill="none" stroke-linecap="round"/>'
    else:
        mouth = f'<line x1="{cx-12}" y1="{cy+size*0.35}" x2="{cx+12}" y2="{cy+size*0.35}" stroke="#555" stroke-width="3" stroke-linecap="round"/>'

    # stage別の追加パーツ
    extras = ""
    if stage_index >= 1:
        extras += f'<circle cx="{cx}" cy="{cy-size*0.9}" r="{6+stage_index}" fill="{body_color}" stroke="#555" stroke-width="2"/>'
    if stage_index >= 2:
        extras += (
            f'<path d="M {cx-size*0.6} {cy-size*0.3} L {cx-size*0.95} {cy-size*0.55}" stroke="#555" stroke-width="3" stroke-linecap="round"/>'
            f'<path d="M {cx+size*0.6} {cy-size*0.3} L {cx+size*0.95} {cy-size*0.55}" stroke="#555" stroke-width="3" stroke-linecap="round"/>'
        )
    if stage_index >= 3:
        extras += (
            f'<polygon points="{cx-size*0.25},{cy-size*0.95} {cx-size*0.1},{cy-size*1.25} {cx+size*0.05},{cy-size*0.95}" fill="#fff3b0" stroke="#555" stroke-width="2"/>'
            f'<polygon points="{cx+size*0.1},{cy-size*0.95} {cx+size*0.25},{cy-size*1.3} {cx+size*0.4},{cy-size*0.95}" fill="#fff3b0" stroke="#555" stroke-width="2"/>'
        )
    if stage_index >= 4:
        extras += f'<circle cx="{cx}" cy="{cy}" r="{size*1.35}" fill="none" stroke="#ffd166" stroke-width="3" stroke-dasharray="6 6" opacity="0.7"/>'

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="300" height="300">
  <defs>
    <radialGradient id="bg" cx="50%" cy="40%" r="70%">
      <stop offset="0%" stop-color="#f0f7ff"/>
      <stop offset="100%" stop-color="#dbeafe"/>
    </radialGradient>
  </defs>
  <rect width="300" height="300" rx="20" fill="url(#bg)"/>
  {extras}
  <circle cx="{cx}" cy="{cy}" r="{size}" fill="{body_color}" stroke="#555" stroke-width="3"/>
  <circle cx="{cx-size*0.55}" cy="{cy+size*0.15}" r="{size*0.22}" fill="{cheek_color}" opacity="0.6"/>
  <circle cx="{cx+size*0.55}" cy="{cy+size*0.15}" r="{size*0.22}" fill="{cheek_color}" opacity="0.6"/>
  <circle cx="{cx-eye_offset}" cy="{cy-size*0.1}" r="{eye_r}" fill="#333"/>
  <circle cx="{cx+eye_offset}" cy="{cy-size*0.1}" r="{eye_r}" fill="#333"/>
  {mouth}
  <text x="150" y="280" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#555">{stage['name']} ・ EXP {exp}</text>
</svg>'''
    return svg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="乱数で活動量を模擬するローカルテスト用モード")
    args = parser.parse_args()

    state = load_state()
    now = datetime.now(timezone.utc)

    if args.demo:
        commits = random.randint(0, 4)
        merged_prs = random.randint(0, 1)
        closed_issues = random.randint(0, 2)
    else:
        commits = count_recent_commits()
        merged_prs, closed_issues = count_recent_prs_and_issues(now)

    score = commits * COMMIT_POINTS + merged_prs * PR_POINTS + closed_issues * ISSUE_POINTS
    if score <= 0:
        score = HUNGRY_PENALTY

    state["exp"] = max(0, state.get("exp", 0) + score)
    state["stage_index"] = stage_for_exp(state["exp"])
    state["mood"] = mood_for_score(score)
    state["last_run"] = now.isoformat()

    history = state.get("history", [])
    history.append({
        "date": now.date().isoformat(),
        "score": score,
        "exp": state["exp"],
        "commits": commits,
        "merged_prs": merged_prs,
        "closed_issues": closed_issues,
    })
    state["history"] = history[-HISTORY_LIMIT:]

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    svg = render_svg(state["stage_index"], state["mood"], state["exp"])
    SVG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SVG_PATH.write_text(svg, encoding="utf-8")

    stage_index = state["stage_index"]
    next_stage_exp = STAGES[stage_index + 1]["min_exp"] if stage_index + 1 < len(STAGES) else None

    STATUS_PATH.write_text(json.dumps({
        "last_run": state["last_run"],
        "score": score,
        "stage": STAGES[stage_index]["name"],
        "stage_index": stage_index,
        "stage_min_exp": STAGES[stage_index]["min_exp"],
        "next_stage_exp": next_stage_exp,
        "mood": state["mood"],
        "exp": state["exp"],
        "history": state["history"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"stage={STAGES[state['stage_index']]['name']} mood={state['mood']} exp={state['exp']} score={score}")


if __name__ == "__main__":
    main()
