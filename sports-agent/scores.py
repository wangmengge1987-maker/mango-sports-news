# -*- coding: utf-8 -*-
"""赛事比分采集 — ESPN 公开 Scoreboard API（无需 Key）"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import requests

import config


def _fetch_espn_scoreboard(url: str) -> List[Dict[str, Any]]:
    """调用 ESPN Scoreboard API，返回标准化比赛列表"""
    try:
        params = {
            "limit": 50,
            "dates": datetime.now(timezone.utc).strftime("%Y%m%d"),
        }
        resp = requests.get(url, params=params, timeout=15,
                            headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[WARN] ESPN 比分接口请求失败: {e}")
        return []

    games = []
    for event in data.get("events", []):
        try:
            comp = event["competitions"][0]
            competitors = comp.get("competitors", [])

            if len(competitors) < 2:
                continue

            home = competitors[0] if competitors[0].get("homeAway") == "home" else competitors[1]
            away = competitors[1] if competitors[0].get("homeAway") == "away" else competitors[0]

            home_score = home.get("score", "")
            away_score = away.get("score", "")
            status = comp.get("status", {}).get("type", {}).get("description", "")

            game = {
                "home_team": home.get("team", {}).get("displayName", ""),
                "home_score": home_score,
                "away_team": away.get("team", {}).get("displayName", ""),
                "away_score": away_score,
                "status": status,
                "date": event.get("date", ""),
            }
            games.append(game)
        except (KeyError, IndexError) as e:
            print(f"[WARN] 解析比赛条目异常: {e}")
            continue

    return games


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
        print(f"[INFO] 正在采集 {league} 比分: {cfg['url']}")
        games = _fetch_espn_scoreboard(cfg["url"])
        print(f"[INFO] {league}: 获取到 {len(games)} 场比赛")
        result[league] = games
    return result
