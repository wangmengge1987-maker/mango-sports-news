# -*- coding: utf-8 -*-
"""新闻翻译模块 — 将英文新闻翻译为中文"""

import re
import hashlib
import os
import json
from typing import Dict, Any, List, Optional

import config

# 翻译缓存（避免重复请求）
_cache_dir = os.path.join(os.path.dirname(__file__), ".trans_cache")
os.makedirs(_cache_dir, exist_ok=True)


def _cache_key(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _cache_get(key: str) -> Optional[str]:
    path = os.path.join(_cache_dir, f"{key}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("translation")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _cache_set(key: str, translation: str):
    path = os.path.join(_cache_dir, f"{key}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"translation": translation}, f, ensure_ascii=False)
    except OSError:
        pass


def _is_mostly_english(text: str) -> bool:
    """判断文本是否以英文为主（需要翻译）"""
    if not text:
        return False
    # 如果包含大量 CJK 字符，就不需要翻译
    cjk = sum(1 for c in text if '一' <= c <= '鿿')
    total = len(text.strip())
    if total == 0:
        return False
    return cjk / total < 0.3


def translate_text(text: str, src: str = "auto", dst: str = "zh") -> str:
    """翻译单段文本，失败则返回原文"""
    if not text or not _is_mostly_english(text):
        return text

    key = _cache_key(f"{text}|{src}|{dst}")
    cached = _cache_get(key)
    if cached is not None:
        return cached

    try:
        import translators as ts
        result = ts.translate_text(text, translator="bing", from_language=src, to_language=dst)
        if result and result.strip():
            _cache_set(key, result.strip())
            return result.strip()
        return text
    except Exception as e:
        print(f"  [WARN] 翻译失败: {e}")
        return text


def batch_translate(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量翻译条目中的标题和摘要"""
    total = len(entries)
    need_translate = [(i, e) for i, e in enumerate(entries) if _is_mostly_english(e.get("title", ""))]

    if not need_translate:
        return entries

    print(f"[INFO] 翻译中: {len(need_translate)}/{total} 条需要翻译")

    for idx, (orig_idx, entry) in enumerate(need_translate):
        if idx % 5 == 0:
            print(f"  [{idx+1}/{len(need_translate)}]...")

        # 翻译标题
        title_en = entry.get("title", "")
        title_cn = translate_text(title_en)
        if title_cn and title_cn != title_en:
            entry["title_cn"] = title_cn
        else:
            entry["title_cn"] = title_en

        # 翻译摘要
        summary_en = entry.get("summary", "")
        # 只翻译前 500 字符（节省请求）
        summary_trunc = summary_en[:500]
        summary_cn = translate_text(summary_trunc)
        if summary_cn and summary_cn != summary_trunc:
            entry["summary_cn"] = summary_cn
        else:
            entry["summary_cn"] = summary_en

    print(f"[INFO] 翻译完成")
    return entries


def translate_classified(classified: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """翻译所有分类下的新闻条目"""
    # 收集所有需要翻译的条目
    all_entries = []
    for items in classified.values():
        all_entries.extend(items)

    if not all_entries:
        return classified

    # 批量翻译（内部会判断是否需要翻译）
    batch_translate(all_entries)
    return classified
