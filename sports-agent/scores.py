# -*- coding: utf-8 -*-
"""赛事比分采集 — ESPN 公开 Scoreboard API（无需 Key）
   包含球员表现数据：得分王、篮板王、助攻王等"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import requests

import config


def _fetch_espn_scoreboard(url: str, league: str = "nba") -> List[Dict[str, Any]]:
    """调用 ESPN Scoreboard API，返回标准化比赛列表（含球员亮点）"""
    today = datetime.now(timezone.utc)

    all_games = []
    # 回查最近 N 天（比赛日可能不在今天）
    for offset in range(config.SCORE_LOOKBACK_DAYS + 1):
        day = today - timedelta(days=offset)
        date_str = day.strftime("%Y%m%d")
        try:
            params = {"limit": 50, "dates": date_str}
            resp = requests.get(
                url, params=params, timeout=15,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  [WARN] ESPN {date_str} 请求失败: {e}")
            continue

        for event in data.get("events", []):
            try:
                game = _parse_event(event, league)
                if game:
                    all_games.append(game)
            except Exception as e:
                print(f"  [WARN] 解析比赛异常: {e}")
                continue

    # 去重（同场比赛可能出现在不同日期的查询结果中）
    seen = set()
    unique = []
    for g in all_games:
        dedup_key = (g["home_team"], g["away_team"], g["date"][:10])
        if dedup_key not in seen:
            seen.add(dedup_key)
            unique.append(g)

    return unique


def _parse_event(event: Dict[str, Any], league: str = "nba") -> Optional[Dict[str, Any]]:
    """解析单场比赛，包含球员表现数据"""
    comp = event["competitions"][0]
    competitors = comp.get("competitors", [])
    if len(competitors) < 2:
        return None

    home = next(c for c in competitors if c.get("homeAway") == "home")
    away = next(c for c in competitors if c.get("homeAway") == "away")

    status_type = comp.get("status", {}).get("type", {})
    status = status_type.get("description", "")

    # 只保留已完赛的比赛
    if status not in ("Final", "Finished"):
        return None

    home_score = home.get("score", "")
    away_score = away.get("score", "")

    game = {
        "home_team": home.get("team", {}).get("displayName", ""),
        "home_score": home_score,
        "away_team": away.get("team", {}).get("displayName", ""),
        "away_score": away_score,
        "status": status,
        "date": event.get("date", ""),
        "highlights": _build_highlights(home, away, league),
    }
    return game


def _build_highlights(
    home: Dict, away: Dict, league: str = "nba"
) -> Dict[str, List[Dict[str, Any]]]:
    """从两队数据中提取球员表现亮点"""
    result = {"home": [], "away": []}

    for side, team_data in [("home", home), ("away", away)]:
        leaders = team_data.get("leaders", [])
        highlights = []

        for leader_cat in leaders:
            category = leader_cat.get("name", "")
            top_performers = leader_cat.get("leaders", [])
            for perf in top_performers[:2]:  # 每类最多 2 人
                athlete = perf.get("athlete", {})
                name = athlete.get("displayName", "")
                value = perf.get("value", 0)
                if name and value:
                    # 整理数值：评分类保留1位小数，其余取整
                    if category == "rating":
                        cleaned = round(value, 1)
                    else:
                        cleaned = int(round(value)) if isinstance(value, (int, float)) else value
                    highlights.append({
                        "player": name,
                        "category": category,
                        "value": cleaned,
                    })

        # 按评分排序，取最重要数据
        result[side] = sorted(
            highlights,
            key=lambda x: {"points": 10, "goals": 10, "assists": 7,
                           "rebounds": 8, "rating": 9, "goalsLeaders": 6}.get(
                x["category"], 5
            ),
            reverse=True,
        )

    return result


def collect_scores() -> Dict[str, List[Dict[str, Any]]]:
    """采集所有启用的联赛比分"""
    result = {}
    for league, cfg in config.SCORE_SOURCES.items():
        if not cfg.get("enabled"):
            continue
        if "url" not in cfg:
            print(f"[INFO] {league} 暂无公开比分接口，跳过")
            result[league] = []
            continue

        print(f"[INFO] 正在采集 {league} 比分及球员数据: {cfg['url']}")
        # 注入 league 标识
        games = _fetch_espn_scoreboard(cfg["url"], league)
        for g in games:
            g["_league"] = league
        print(f"[INFO] {league}: 获取到 {len(games)} 场完赛比赛")
        result[league] = games
    return result
