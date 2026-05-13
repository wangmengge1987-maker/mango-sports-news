# -*- coding: utf-8 -*-
"""RSS 新闻采集器"""

import feedparser
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any
import config


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


import re

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

    # 分类
    classified = classify(recent)
    return classified
