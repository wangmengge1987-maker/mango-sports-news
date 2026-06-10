# -*- coding: utf-8 -*-
"""文章历史记录管理——跨日去重"""

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Set, List, Dict, Any, Optional

HISTORY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "output", ".article_history.json"
)
CONTENT_HASH_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "output", ".content_hash_history.json"
)


def load_history() -> Set[str]:
    """加载已报道文章 URL 集合"""
    if not os.path.exists(HISTORY_FILE):
        return set()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.keys())
    except (json.JSONDecodeError, IOError):
        return set()


def save_history(urls: Set[str]) -> None:
    """追加新文章 URL 到历史记录"""
    existing = {}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    now = datetime.now(timezone.utc).isoformat()
    for url in urls:
        if url not in existing:
            existing[url] = now

    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def prune_history(days: int = 14) -> int:
    """清理超过 N 天的历史记录，返回清理条数"""
    if not os.path.exists(HISTORY_FILE):
        return 0
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    before = len(data)
    data = {url: ts for url, ts in data.items()
            if datetime.fromisoformat(ts) > cutoff}
    after = len(data)

    if after < before:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return before - after


def filter_new(entries: List[Dict[str, Any]], history: Set[str]) -> List[Dict[str, Any]]:
    """过滤掉已在历史中的文章（按 URL）"""
    return [e for e in entries if e.get("link") not in history]


# ─── 内容哈希历史（相同文章不同 URL 去重） ──────────────────────

def load_hash_history() -> Set[str]:
    """加载已报道内容哈希集合"""
    if not os.path.exists(CONTENT_HASH_FILE):
        return set()
    try:
        with open(CONTENT_HASH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.keys())
    except (json.JSONDecodeError, IOError):
        return set()


def save_hash_history(hashes: Set[str]) -> None:
    """追加新内容哈希到历史记录"""
    existing = {}
    if os.path.exists(CONTENT_HASH_FILE):
        try:
            with open(CONTENT_HASH_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    now = datetime.now(timezone.utc).isoformat()
    for h in hashes:
        if h not in existing:
            existing[h] = now

    os.makedirs(os.path.dirname(CONTENT_HASH_FILE), exist_ok=True)
    with open(CONTENT_HASH_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def filter_new_by_hash(entries: List[Dict[str, Any]], hash_history: Set[str], hash_field: str = "content_hash") -> List[Dict[str, Any]]:
    """过滤掉已在历史中（按内容哈希）的文章"""
    return [e for e in entries if e.get(hash_field) not in hash_history]


def prune_hash_history(days: int = 30) -> int:
    """清理超过 N 天的内容哈希历史记录"""
    if not os.path.exists(CONTENT_HASH_FILE):
        return 0
    try:
        with open(CONTENT_HASH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    before = len(data)
    data = {h: ts for h, ts in data.items()
            if datetime.fromisoformat(ts) > cutoff}
    after = len(data)

    if after < before:
        with open(CONTENT_HASH_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return before - after


def get_last_save_time() -> datetime:
    """获取历史记录最近一次保存的时间（所有条目中最晚的时间戳）"""
    if not os.path.exists(HISTORY_FILE):
        return None
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data:
            return None
        latest = max(
            (datetime.fromisoformat(ts) for ts in data.values()),
            default=None,
        )
        return latest
    except (json.JSONDecodeError, IOError, ValueError):
        return None


def reset_history() -> int:
    """清空历史记录，返回删除条数"""
    count = 0
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                count = len(json.load(f))
        except (json.JSONDecodeError, IOError):
            pass
        os.remove(HISTORY_FILE)
    return count
