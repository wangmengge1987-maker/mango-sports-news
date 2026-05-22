# -*- coding: utf-8 -*-
"""RSS 新闻采集器"""

import feedparser
import requests
import re
from datetime import datetime, timezone
from typing import List, Dict, Any
import config


def _strip_html_tags(text: str) -> str:
    """Remove HTML tags like <font color=...> <em> from text"""
    return re.sub(r'<[^>]+>', '', text) if text else ""


_VIDEO_PATTERNS = re.compile(
    r"(^video[:\s]|^watch[:\s]|精彩视频|视频集锦|每周足球视频|录像|回放|"
    r"最佳进球|十佳球|top\s*10|weekly\s+video|match\s+highlights|"
    r"highlights\s*:|集锦$)",
    re.IGNORECASE,
)

def _is_video_content(entry: Dict[str, Any]) -> bool:
    """判断是否为纯视频内容（文本推送中无法观看，应过滤）"""
    title = entry.get("title", "")
    summary = entry.get("summary", "")
    text = f"{title} {summary}"
    if _VIDEO_PATTERNS.search(text):
        return True
    # 摘要过短或为空且标题含视频暗示
    if len(summary.strip()) < 20 and ("video" in title.lower() or "watch" in title.lower()):
        return True
    return False


def _is_gibberish_translation(text: str) -> bool:
    """判断中文翻译是否疑似劣质（语无伦次 / 无效信息）"""
    # 连续出现 3+ 个"的"  eg: 的五花八门的队伍 → 劣质翻译信号
    if text.count("的") >= 3 and len(text) < 30:
        return True
    # 包含未翻译的英文长词
    en_words = re.findall(r"[a-zA-Z]{6,}", text)
    if len(en_words) >= 2:
        return True
    return False


def clean_entry(entry: Dict[str, Any]) -> bool:
    """清洗单条新闻：True=保留, False=丢弃"""
    title = entry.get("title", "").strip()
    if not title:
        return False
    if _is_video_content(entry):
        return False
    return True


def fetch_dongqiudi(keyword: str, max_items: int = 10) -> List[Dict[str, Any]]:
    """从懂球帝搜索 API 采集新闻"""
    try:
        resp = requests.get(
            "http://api.dongqiudi.com/search",
            params={"keywords": keyword, "type": "all", "page": 1},
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[WARN] 懂球帝 API 请求失败 ({keyword}): {e}")
        return []

    entries = []
    for item in data.get("news", [])[:max_items]:
        try:
            title = _strip_html_tags(item.get("title", ""))
            summary = _strip_html_tags(item.get("description", ""))
            pub_str = item.get("pubdate", "")
            try:
                published = datetime.strptime(pub_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                published = datetime.now(timezone.utc)
            # 构建可访问的网页链接
            link = ""
            raw_url = item.get("url1") or item.get("url", "")
            news_id = item.get("id", "")
            if raw_url:
                # dongqiudi:///news/123 → https://www.dongqiudi.com/news/123
                m = re.search(r'/(?:news|article|feed)/(\d+)', raw_url)
                if m:
                    link = f"https://www.dongqiudi.com/{'article' if '/article/' in raw_url else 'news'}/{m.group(1)}"
            if not link and news_id:
                link = f"https://www.dongqiudi.com/news/{news_id}"
            entries.append({
                "title": title,
                "summary": summary,
                "link": link,
                "published": published,
                "source": f"懂球帝 ({keyword})",
            })
        except Exception as e:
            print(f"  [WARN] 解析懂球帝条目异常: {e}")
            continue

    print(f"[INFO] 懂球帝 ({keyword}): 获取到 {len(entries)} 条")
    return entries


def fetch_rss(url: str, timeout: int = 15) -> List[Dict[str, Any]]:
    """抓取 RSS 并返回标准化条目列表"""
    try:
        # 先用 feedparser 解析
        parsed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
        if parsed.bozo and not parsed.entries:
            # fallback: requests 拉取原始 XML 再解析
            resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            parsed = feedparser.parse(resp.text)

        entries = []
        for entry in parsed.entries:
            # 解析发布时间
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            else:
                published = datetime.now(timezone.utc)

            entries.append({
                "title": getattr(entry, "title", "无标题"),
                "summary": getattr(entry, "summary", getattr(entry, "description", "")),
                "link": getattr(entry, "link", ""),
                "published": published,
            })
        return entries
    except Exception as e:
        print(f"[WARN] RSS 抓取失败 {url}: {e}")
        return []


def _build_matchers():
    """为每类关键词构建匹配器：英文用 \\b 词边界，中文用子串匹配"""
    matchers = {}
    for cat, cfg in config.CATEGORIES.items():
        patterns = []
        for kw in cfg["keywords"]:
            kw_lower = kw.lower()
            # 是否包含 CJK 字符（一-鿿）
            if any('一' <= c <= '鿿' for c in kw):
                patterns.append(re.compile(re.escape(kw_lower)))
            else:
                patterns.append(re.compile(r'\b' + re.escape(kw_lower) + r'\b'))
        matchers[cat] = patterns
    return matchers

def classify(entries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """按关键词对新闻进行分类"""
    result = {cat: [] for cat in config.CATEGORIES}
    result["其他"] = []
    patterns = _build_matchers()

    for entry in entries:
        text = f"{entry['title']} {entry['summary']}".lower()
        matched = False
        for cat in config.CATEGORIES:
            for pat in patterns[cat]:
                if pat.search(text):
                    result[cat].append(entry)
                    matched = True
                    break
            if matched:
                break
        if not matched:
            result["其他"].append(entry)
    return result


def filter_recent(entries: List[Dict[str, Any]], window=config.TIME_WINDOW) -> List[Dict[str, Any]]:
    """只保留时间窗口内的新闻"""
    now = datetime.now(timezone.utc)
    return [e for e in entries if (now - e["published"]) <= window]


def collect_all() -> Dict[str, List[Dict[str, Any]]]:
    """主入口：抓取所有源，过滤，分类，去重"""
    all_entries = []
    for src in config.RSS_SOURCES:
        print(f"[INFO] 正在抓取: {src['name']} ({src['url']})")
        entries = fetch_rss(src["url"])
        for e in entries:
            e["source"] = src["name"]
        all_entries.extend(entries)

    # 去重（按链接）
    seen = set()
    unique = []
    for e in all_entries:
        if e["link"] and e["link"] not in seen:
            seen.add(e["link"])
            unique.append(e)

    # 过滤24小时内
    recent = filter_recent(unique)
    print(f"[INFO] 去重后共 {len(unique)} 条，24小时内 {len(recent)} 条")

    # 清洗：过滤视频类、劣质翻译等
    before = len(recent)
    recent = [e for e in recent if clean_entry(e)]
    if before - len(recent):
        print(f"[INFO] 清洗过滤: 移除 {before - len(recent)} 条低质量内容")

    # 分类
    classified = classify(recent)

    # 采集懂球帝（中文体育新闻，跳过 24h 过滤）
    dq_sources = getattr(config, "DONGQIUDI_SOURCES", [])
    if dq_sources:
        print("")
        print("[INFO] 正在采集懂球帝...")
        dq_max = getattr(config, "DONGQIUDI_MAX_ITEMS", 10)
        dq_all = []
        for dq in dq_sources:
            if dq.get("enabled", True):
                entries = fetch_dongqiudi(dq["keywords"], dq_max)
                for e in entries:
                    e["source"] = dq["name"]
                dq_all.extend(entries)
        # 去重（按链接）
        seen = set()
        dq_unique = []
        for e in dq_all:
            if e["link"] and e["link"] not in seen:
                seen.add(e["link"])
                dq_unique.append(e)
        if dq_unique:
            dq_classified = classify(dq_unique)
            print(f"[INFO] 懂球帝: 分类后 {sum(len(v) for v in dq_classified.values())} 条")
            for cat, items in dq_classified.items():
                if items:
                    classified.setdefault(cat, [])
                    classified[cat] = items + classified[cat]

    return classified
