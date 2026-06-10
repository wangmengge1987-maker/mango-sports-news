# -*- coding: utf-8 -*-
"""Markdown 简报生成器 — 支持比赛结果 + 新闻 + 推送版"""

import os
import re
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
            for league in ["NBA", "英超", "中超"]:
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
            title = (item.get("title_cn") or item["title"]).strip()
            summary = clean_html(item.get("summary_cn") or item["summary"])[:200]
            raw_summary = clean_html(item.get("summary_cn") or item["summary"])
            link = item["link"]
            pub = item["published"].strftime("%m-%d %H:%M") if item["published"] else "未知时间"
            source = item.get("source", "未知来源")

            # 比赛报道 → 用一句话结果替换原标题
            game_result = _extract_game_result(item)
            display_title = game_result if game_result else title

            lines.append(f"{idx}. **{display_title}**")
            if not game_result:
                lines.append(f"   - {summary}{'...' if len(raw_summary) > 200 else ''}")
            lines.append(f"   - {source} | {pub}")
            lines.append(f"   - [原文链接]({link})")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _is_useful_title(title: str) -> bool:
    """推送标题质量检查：跳过太短、纯视频、翻译劣质的标题"""
    t = title.strip()
    if len(t) < 8:
        return False
    # 视频类关键词
    if re.search(r"(精彩视频|视频集锦|每周.*视频|录像|回放|highlight|集锦$)", t, re.IGNORECASE):
        return False
    # 逐词硬译标志：X的Y的（如"森林狼队的五花八门的队伍"）
    if re.search(r"\w+的\w+的", t):
        return False
    return True


def _extract_game_result(item: Dict[str, Any]) -> Optional[str]:
    """从比赛报道摘要中提取一句话结果：比分、胜负、关键信息"""
    title = clean_html((item.get("title_cn") or item["title"]).strip())
    summary = clean_html(item.get("summary_cn") or item.get("summary", ""))
    text = f"{title}. {summary}"

    # 查找比分模式: 1-0, 112-108, 3比1
    score = None
    m = re.search(r'(\d+)\s*[-–—]\s*(\d+)', text)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        # 双方 >= 50 可能是生涯战绩（如"going 189-221"），需额外确认比赛语境
        is_game_context = bool(re.search(
            r"(defeated|beat\b|won\b|win\b|victory|score|goal|击败|战胜|胜\s|负\s|比赛|进球)",
            text, re.IGNORECASE,
        ))
        if a < 50 or b < 50 or is_game_context:
            score = m.group(0)
    if not score:
        m = re.search(r'(\d+)\s*比\s*(\d+)', text)
        if m:
            score = f"{m.group(1)}-{m.group(2)}"

    if not score:
        return None

    # 只在前 300 字符内查找（比赛报道首个句子就包含比分）
    head = text[:300]
    sentences = re.split(r'(?<=[.!?。！？])\s*', head)
    for s in sentences:
        if score.replace(' ', '') in s.replace(' ', '') or score in s:
            result = s.strip().strip('*"\'"" ').strip()
            if len(result) > 100:
                result = result[:97] + "..."
            return result

    return None


_TRAILING_ELLIPSIS = re.compile(r"[….]{2,}\s*$")


_LIST_ARTICLE_PATTERN = re.compile(
    r'(\d+\s*(?:件事|个问题|个看点|个话题|个关注|大看点|things|ways|reasons|'
    r'to\s*watch|to\s*know|stories|moments|players|questions))',
    re.IGNORECASE,
)


def _article_one_liner(item: Dict[str, Any]) -> str:
    """生成一句话文章概要：比赛结果优先 → 全文背景 → 标题+摘要组合 → 回退标题"""
    # 1. 比赛报道 → 比分结果
    game = _extract_game_result(item)
    if game:
        return game

    title = clean_html((item.get("title_cn") or item["title"]).strip())
    summary = clean_html(item.get("summary_cn") or item.get("summary", ""))

    # 2. 优先使用抓取到的全文背景（包含故事的"为什么"）
    full_context = item.get("full_context", "")
    if full_context and len(full_context) > 30:
        result = f"{title} —— {full_context}"
        if len(result) > 300:
            result = result[:297] + "..."
        return result

    # 3. 从摘要中提取内容（但要检查摘要是否完整/含必要信息）
    if summary and len(summary) > 25:
        clean_summary = re.sub(r'\s+', ' ', summary).strip()

        # 检查摘要是否截断（不以句号/感叹号/问号/完整英文单词结尾）
        _is_truncated = (
            not re.search(r'[。！？.!?]\s*$', clean_summary)
            and re.search(r'[a-zA-Z]{2,}$', clean_summary)  # 以英文词结尾 → 可能截断
        )

        # 检查标题中的关键信息是否在摘要中缺失
        # 提取标题中的中文人名/队名（2-6字的中文词语）
        title_entities = set(re.findall(r'[一-鿿]{2,6}', title))
        # 提取摘要中同样长度的中文词语
        summary_entities = set(re.findall(r'[一-鿿]{2,6}', clean_summary))
        # 标题中出现在摘要之外的关键实体
        missing_entities = title_entities - summary_entities

        # 如果摘要截断，或关键信息缺失，优先用标题
        if _is_truncated or (missing_entities and len(title) >= 8):
            # 用标题为主，摘要补充
            result = title
            # 取摘要的第一句作为补充（但不包含截断部分）
            first_sentence = clean_summary.split('。')[0].strip() if '。' in clean_summary else clean_summary[:40]
            if len(first_sentence) > 10 and first_sentence not in result:
                if len(result) + len(first_sentence) + 3 < 120:
                    result = f"{result}：{first_sentence}"
            if len(result) > 120:
                result = result[:117] + "..."
            return result

        sentences = re.split(r'(?<=[.!?。！？])\s*', clean_summary)

        # 列表类文章（"X件事/个看点"）：提取更多具体内容
        if _LIST_ARTICLE_PATTERN.search(title):
            excerpt = ""
            for s in sentences:
                s = s.strip().strip('"\'""')
                if not s or len(s) < 8:
                    continue
                if len(excerpt) + len(s) > 250:
                    break
                excerpt += s + " "
            excerpt = excerpt.strip()
            if len(excerpt) > 30:
                if len(excerpt) > 250:
                    excerpt = excerpt[:247] + "..."
                return excerpt

        # 普通文章：提取第一句有信息量的句子
        first = sentences[0].strip() if sentences else ""
        first = re.sub(r'^[""\'""]+|[""\'""]+$', "", first).strip()
        first = _TRAILING_ELLIPSIS.sub("", first).strip()
        if len(first) > 15:
            # 检查第一句是否包含代词而非具体名称
            _has_vague_pronoun = bool(re.search(r'[他她它]', first)) and not any(
                e in first for e in title_entities
            )
            if _has_vague_pronoun:
                # 摘要以代词开头但缺具体名称 → 补充标题
                if len(title) + len(first) + 3 < 120:
                    return f"{title}：{first}"
            if len(first) > 120:
                first = first[:117] + "..."
            return first

    # 4. 回退：清理原标题（确保完整表述）
    title = _TRAILING_ELLIPSIS.sub("", title).strip()
    # 确保标题包含完整信息（长度足够且有具体内容）
    if len(title) >= 8 and not re.match(r'^[他她它这那]', title):
        return title
    return title if len(title) >= 12 else ""


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

    # ─── 比赛结果（含球员亮点） ──────────────────────────
    if scores:
        for league in ["NBA", "英超", "中超"]:
            games = scores.get(league, [])
            # 显示最近 N 天的完赛结果（不限于今天）
            recent = sorted(games, key=lambda g: g.get("date", ""), reverse=True)[:6]
            if not recent:
                continue

            lines.append(f"**{league} 赛果:**")
            for g in recent:
                score_line = (f"  {g['away_team']} {g['away_score']} - "
                              f"{g['home_score']} {g['home_team']}")
                lines.append(score_line)

                # 球员亮点
                hl = _format_highlights(g, league)
                if hl:
                    lines.append(f"    {hl}")
                # 发挥失常 / 空砍
                ll = _format_lowlights(g)
                if ll:
                    lines.append(f"    {ll}")

            lines.append("")

    # ─── 新闻摘要 ──────────────────────────────────────
    priority_order = ["NBA", "CBA", "英超", "中超", "伤病", "转会"]
    for cat in priority_order:
        items = classified.get(cat, [])
        if not items:
            continue
        lines.append(f"**{cat}:**")
        sorted_items = sorted(items, key=lambda x: x["published"], reverse=True)
        count = 0
        for item in sorted_items:
            if count >= 3:
                break
            one_liner = _article_one_liner(item)
            if not one_liner or not _is_useful_title(one_liner):
                continue
            lines.append(f"  - {one_liner}")
            count += 1
        if count == 0:
            lines.pop()  # remove the category header
        lines.append("")

    text = "\n".join(lines)

    if len(text) > config.MAX_PUSH_LENGTH:
        # 在行边界截断：取前 MAX_PUSH_LENGTH 字符范围内最后一个换行符位置
        text = text[:config.MAX_PUSH_LENGTH]
        last_nl = text.rfind('\n')
        if last_nl > 0:
            text = text[:last_nl]
        text += "\n\n...(内容较长，已截断保留主要摘要)"

    return text


_CATEGORY_LABELS = {
    "points": "分",
    "goals": "进球",
    "goalsLeaders": "进球",
    "assists": "助攻",
    "rebounds": "篮板",
    "rating": "评分",
}


def _format_lowlights(game: dict) -> str:
    """从比赛数据中找出"空砍"或发挥失常的情况"""
    highlights = game.get("highlights", {})
    if not highlights:
        return ""

    home_score = int(game.get("home_score", 0) or 0)
    away_score = int(game.get("away_score", 0) or 0)

    # 找出输球方 —— 那就是"空砍"
    losing_side = None
    if home_score < away_score:
        losing_side = "home"
    elif away_score < home_score:
        losing_side = "away"

    if not losing_side:
        return ""

    team_hl = highlights.get(losing_side, [])
    # 篮球找 "points"，足球找 "goals"
    top_scorer = next(
        (h for h in team_hl if h["category"] in ("points", "goals", "goalsLeaders")),
        None,
    )
    if top_scorer:
        diff = abs(home_score - away_score)
        unit = "分" if top_scorer["category"] == "points" else "球"
        return f"[注意] {top_scorer['player']} 独进{top_scorer['value']}{unit}，球队仍输{diff}分"

    return ""


def _format_highlights(game: dict, league: str) -> str:
    """从比赛数据中生成球员亮点字符串"""
    highlights = game.get("highlights", {})
    if not highlights:
        return ""

    parts = []
    seen_players = set()  # 同队同项不重复

    for side, label in [("away", "客"), ("home", "主")]:
        team_hl = highlights.get(side, [])
        if not team_hl:
            continue

        for h in team_hl:
            player = h["player"]
            if player in seen_players:
                continue
            seen_players.add(player)

            # 整理数值：浮点转整数
            raw = h["value"]
            val = int(raw) if isinstance(raw, (int, float)) and raw == int(raw) else raw

            label_text = _CATEGORY_LABELS.get(h["category"], h["category"])
            parts.append(f"{player} {val}{label_text}")

    if not parts:
        return ""

    # 取前 4 条最有价值的数据
    result = " | ".join(parts[:4])
    if len(result) > 150:
        result = result[:147] + "..."

    return f"[球员] {result}"


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
