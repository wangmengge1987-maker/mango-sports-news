# -*- coding: utf-8 -*-
"""Markdown 简报生成器 — 支持比赛结果 + 新闻 + 推送版"""

import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from html.parser import HTMLParser

import config


class _MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return "".join(self.fed)


def clean_html(raw: str) -> str:
    """去除 HTML 标签"""
    s = _MLStripper()
    try:
        s.feed(raw)
        return s.get_data().strip()
    except Exception:
        return raw


def _scores_table(games: List[Dict[str, Any]], league: str) -> List[str]:
    """生成比分表格"""
    if not games:
        return [f"暂无 {league} 比赛数据", ""]

    lines = [
        "| 客队 | 比分 | 主队 | 状态 |",
        "|------|:----:|------|:----:|",
    ]
    today = datetime.now().strftime("%Y-%m-%d")
    for g in games:
        # 只显示今天的比赛
        if not g.get("date", "").startswith(today):
            continue
        lines.append(
            f"| {g['away_team']} | {g['away_score']} - {g['home_score']} "
            f"| {g['home_team']} | {g['status']} |"
        )
    # 如果今天没有比赛
    if len(lines) == 2:
        lines = [f"今日暂无 {league} 赛程", ""]
    return lines


def _league_emoji(league: str) -> str:
    """分类对应图标（纯文本，避免 emoji 问题）"""
    mapping = {
        "NBA": "[NBA]", "CBA": "[CBA]",
        "英超": "[EPL]", "中超": "[CSL]",
        "伤病": "[伤病]", "转会": "[转会]",
    }
    return mapping.get(league, f"[{league}]")


def generate_md(
    classified: Dict[str, List[Dict[str, Any]]],
    scores: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> str:
    """生成完整 Markdown 简报"""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    lines = [
        f"# 今日体育简报 ({today})",
        "",
        f"> 自动生成于 {now.strftime('%Y-%m-%d %H:%M')}",
        "> 覆盖过去24小时重点新闻及赛事",
        "",
        "---",
        "",
    ]

    # ─── 1. 比赛结果 ──────────────────────────────────
    if scores:
        has_scores = any(v for v in scores.values())
        if has_scores:
            lines.append("## 昨日/今日 比赛结果")
            lines.append("")
            for league in ["NBA", "英超"]:
                league_games = scores.get(league, [])
                if not league_games:
                    continue
                lines.append(f"### {_league_emoji(league)} {league}")
                lines.append("")
                lines.extend(_scores_table(league_games, league))
                lines.append("")
            lines.append("---")
            lines.append("")

    # ─── 2. 新闻分类 ──────────────────────────────────
    priority_order = ["NBA", "CBA", "英超", "中超", "伤病", "转会", "其他"]

    for cat in priority_order:
        items = classified.get(cat, [])
        if not items:
            continue

        lines.append(f"## {_league_emoji(cat)} {cat}")
        lines.append("")

        sorted_items = sorted(items, key=lambda x: x["published"], reverse=True)
        for idx, item in enumerate(sorted_items[:config.MAX_ITEMS_PER_CATEGORY], 1):
            title = item["title"].strip()
            summary = clean_html(item["summary"])[:200]
            link = item["link"]
            pub = item["published"].strftime("%m-%d %H:%M") if item["published"] else "未知时间"
            source = item.get("source", "未知来源")

            lines.append(f"{idx}. **{title}**")
            lines.append(f"   - {summary}{'...' if len(clean_html(item['summary'])) > 200 else ''}")
            lines.append(f"   - {source} | {pub}")
            lines.append(f"   - [原文链接]({link})")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def generate_push_text(
    classified: Dict[str, List[Dict[str, Any]]],
    scores: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> str:
    """生成适合推送的短版简报（纯文字，控制长度）"""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    lines = [
        f"**今日体育简报 ({today})**",
        f"_{now.strftime('%H:%M')} 更新_",
        "",
    ]

    # ─── 比赛结果（一句话摘要） ──────────────────────────
    if scores:
        for league in ["NBA", "英超"]:
            games = scores.get(league, [])
            today_games = [
                g for g in games
                if g.get("date", "").startswith(today)
            ]
            if today_games:
                lines.append(f"**{league} 今日赛果:**")
                for g in today_games:
                    lines.append(f"  {g['away_team']} {g['away_score']} - {g['home_score']} {g['home_team']} ({g['status']})")
                lines.append("")

    # ─── 新闻摘要 ──────────────────────────────────────
    priority_order = ["NBA", "CBA", "英超", "中超", "伤病", "转会"]
    for cat in priority_order:
        items = classified.get(cat, [])
        if not items:
            continue
        lines.append(f"**{cat}:**")
        sorted_items = sorted(items, key=lambda x: x["published"], reverse=True)
        for item in sorted_items[:3]:
            title = clean_html(item["title"].strip())
            lines.append(f"  - {title}")
        lines.append("")

    text = "\n".join(lines)

    if len(text) > config.MAX_PUSH_LENGTH:
        text = text[:config.MAX_PUSH_LENGTH] + "\n\n..."

    return text


def save_md(content: str, date_str: str = None) -> str:
    """保存 Markdown 文件"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    filename = f"{date_str}-今日体育简报.md"
    filepath = os.path.join(config.OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[INFO] 简报已保存: {filepath}")
    return filepath
