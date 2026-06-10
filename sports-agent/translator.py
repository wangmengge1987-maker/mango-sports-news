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


def _is_gibberish_translation(text: str, original: str = "") -> bool:
    """判断中文翻译是否疑似劣质（语无伦次 / 无效信息）

    Args:
        text: 翻译后的文本
        original: 原始英文文本（用于对比诊断）
    """
    if not text:
        return False

    # 1. 检查编码是否有问题：包含 Unicode 替换字符
    replacement_count = text.count('�')
    if replacement_count > 0:
        return True

    # 2. 统计正常中文字符占比（翻译结果应至少含30%中文字符）
    cjk = sum(1 for c in text if '一' <= c <= '鿿')
    total = len(text.strip())
    if total > 0 and cjk / total < 0.15:
        return True

    # 3. X的Y的 模式：太短（<= 2 字）的 X 和 Y 表示逐词硬译
    #    如 "森林狼队的五花八门的队伍" -> X="森林狼队" Y="五花八门"（太长不算）
    #    如 "好的" -> 是两个「的」相邻，不是问题
    for m in re.finditer(r'([一-鿿]{1,2})的([一-鿿]{1,2})的', text):
        # 如果 X 和 Y 都较短（<=2字），可能是逐词硬译
        return True

    # 4. 包含过多未翻译的英文长词（>=5 个 6 字母以上的英文词）
    #    允许 1-4 个专有名词（人名 Brenden Aaronson、队名 Timberwolves 等）
    #    体育新闻翻译后常保留英文人名/队名，阈值从3放宽到5避免误杀
    en_words = re.findall(r"[a-zA-Z]{6,}", text)
    if len(en_words) >= 5:
        return True

    return False


def _fix_sports_translation(original_en: str, translated_cn: str) -> str:
    """修正体育术语翻译错误（如 rugby prop → 道具 → 橄榄球）"""
    if not original_en or not translated_cn:
        return translated_cn
    text = translated_cn

    # 橄榄球: "prop"（支柱前锋）被误译为"道具"
    if re.search(r'\b(rugby|prop)\b', original_en, re.IGNORECASE):
        text = re.sub(r'\b道具\b', '橄榄球', text)
        # 把"威尔士橄榄球"改得通顺一些
        text = text.replace('威尔士的橄榄球', '威尔士橄榄球运动员')
        text = text.replace('前威尔士橄榄球运动员的', '前威尔士橄榄球运动员')

    return text


_TRANSLATOR_BACKENDS = ["bing", "alibaba", "google"]  # 按优先级排列


def translate_text(text: str, src: str = "en", dst: str = "zh") -> str:
    """翻译单段文本，失败则返回原文"""
    if not text or not _is_mostly_english(text):
        return text

    # 优先使用新格式 key (en|zh)，兼容旧格式 (auto|zh)
    key_new = _cache_key(f"{text}|en|{dst}")
    cached = _cache_get(key_new)
    if cached is not None:
        return cached

    key_old = _cache_key(f"{text}|auto|{dst}")
    cached = _cache_get(key_old)
    if cached is not None:
        # 迁移到新 key
        _cache_set(key_new, cached)
        return cached

    try:
        import translators as ts
    except ImportError:
        return text

    key = key_new  # 保存 key 以便在循环中使用

    for backend in _TRANSLATOR_BACKENDS:
        try:
            result = ts.translate_text(text, translator=backend, from_language="en", to_language=dst)
            if result and result.strip():
                translated = result.strip()
                # 质量检查：劣质翻译则尝试下一个翻译引擎
                if _is_gibberish_translation(translated, text):
                    print(f"  [WARN] {backend} 翻译质量过低（含乱码或无效字符），尝试下一个翻译引擎...")
                    continue
                _cache_set(key_new, translated)
                return translated
        except Exception as e:
            err_msg = str(e)
            # Google 在中国大陆不可用，跳过不打印
            if "offline" in err_msg.lower() or "google" in err_msg.lower():
                continue
            # Alibaba 翻译内部错误或库 bug，静默跳过
            if "key" in err_msg and "not defined" in err_msg:
                continue
            if "should not be same" in err_msg:
                continue
            print(f"  [WARN] {backend} 翻译失败: {e}")
            continue

    # 所有翻译引擎都失败，记录并返回原文
    print(f"  [WARN] 所有翻译引擎均失败（共尝试 {len(_TRANSLATOR_BACKENDS)} 个），保留原文")
    return text


def batch_translate(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量翻译条目中的标题和摘要"""
    total = len(entries)
    # 判断是否需要翻译：标题或摘要为英文
    need_translate = []
    for i, e in enumerate(entries):
        title_en = e.get("title", "")
        summary_en = e.get("summary", "")
        if _is_mostly_english(title_en) or _is_mostly_english(summary_en):
            need_translate.append((i, e))

    if not need_translate:
        return entries

    print(f"[INFO] 翻译中: {len(need_translate)}/{total} 条需要翻译")

    for idx, (orig_idx, entry) in enumerate(need_translate):
        if idx % 5 == 0:
            print(f"  [{idx+1}/{len(need_translate)}]...")

        # 翻译标题
        title_en = entry.get("title", "")
        if _is_mostly_english(title_en):
            title_cn = translate_text(title_en)
            if title_cn and title_cn != title_en:
                entry["title_cn"] = _fix_sports_translation(title_en, title_cn)
            else:
                entry["title_cn"] = title_en
        else:
            entry["title_cn"] = title_en

        # 翻译摘要
        summary_en = entry.get("summary", "")
        if _is_mostly_english(summary_en):
            # 只翻译前 500 字符（节省请求）
            summary_trunc = summary_en[:500]
            summary_cn = translate_text(summary_trunc)
            if summary_cn and summary_cn != summary_trunc:
                entry["summary_cn"] = _fix_sports_translation(summary_trunc, summary_cn)
            else:
                entry["summary_cn"] = summary_en
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
