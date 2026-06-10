# -*- coding: utf-8 -*-
"""文章全文抓取 — 从 URL 提取正文内容，补充 RSS 摘要的不足"""

import re
import requests
import trafilatura

_MAX_FETCH = 10       # 每次运行最多抓取 N 篇文章（避免太慢）
_FETCHED = set()      # 已抓取过的 URL 集合（防止重复抓取）


def needs_full_text(item: dict) -> bool:
    """判断是否需要抓取全文：RSS 摘要过短或标题太模糊"""
    title = (item.get("title_cn") or item["title"] or "").strip()
    summary = (item.get("summary_cn") or item.get("summary") or "").strip()
    text = f"{title} {summary}"

    # 标题看起来像列表类（"X件事"），但摘要没内容
    if re.search(r'\d+\s*(件事|个看点|个话题|things|ways|reasons)', title, re.IGNORECASE):
        if len(summary) < 100:
            return True

    # 标题含有医疗/情感关键词（需要上下文才能理解）
    if re.search(r'(手术|heart|surgery|transplant|survive|tragedy|'
                 r'injury|伤病|受伤|复出|拯救|挽救|奇迹|emotional|moving)',
                text, re.IGNORECASE):
        if not _has_context(summary):
            return True

    # 摘要太短（< 50 字），可能信息不够
    if len(summary) < 50 and len(title) > 20:
        return True

    # 摘要被截断：不以句号/感叹号/问号结尾，且以英文词结尾
    if summary and len(summary) > 20:
        if not re.search(r'[。！？.!?]\s*$', summary) and re.search(r'[A-Za-z]{2,}$', summary):
            return True

    # 标题中有具体人名/队名，但摘要中用代词替代（"他" "她" "它"）
    if title and summary:
        title_entities = set(re.findall(r'[一-鿿]{2,6}', title))
        summary_entities = set(re.findall(r'[一-鿿]{2,6}', summary))
        if title_entities and summary_entities:
            # 如果摘要中的实体远少于标题，可能需要补充全文
            if len(summary_entities) < len(title_entities) * 0.5 and len(title_entities) >= 2:
                return True

    return False


def _has_context(text: str) -> bool:
    """检查文本是否包含背景/因果说明"""
    return bool(re.search(
        r'(因为|由于|经过|确诊|诊断|患有|接受|接受治疗|'
        r'after|because|due to|diagnosed|underwent|suffered|following)',
        text, re.IGNORECASE,
    ))


def extract_article(url: str, timeout: int = 12) -> str:
    """抓取文章全文，返回正文文本（失败返回空字符串）"""
    if url in _FETCHED:
        return ""
    _FETCHED.add(url)

    try:
        resp = requests.get(
            url, timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
        )
        if resp.status_code != 200:
            return ""
        text = trafilatura.extract(resp.text)
        return text.strip() if text else ""
    except Exception:
        return ""


def get_context_summary(item: dict) -> str:
    """尝试抓取全文，提取有上下文的关键段落"""
    url = item.get("link", "")
    if not url:
        return ""

    full_text = extract_article(url)
    if not full_text:
        return ""

    # 把全文按句子切分，找出包含上下文的关键句
    sentences = re.split(r'(?<=[.!?。！？])\s*', full_text)
    title_keywords = set(
        re.findall(r'[a-zA-Z]{4,}', item.get("title", "")[:60].lower())
    )

    key_sentences = []
    for s in sentences:
        s = s.strip()
        if len(s) < 20:
            continue

        # 包含背景/因果/关键词的句子优先
        score = 0
        if _has_context(s):
            score += 2
        # 标题中出现的实词在正文中也出现 → 相关性高
        if title_keywords:
            matched = sum(1 for kw in title_keywords if kw in s.lower())
            score += matched * 0.5
        if score > 0:
            key_sentences.append((score, s))

    # 按得分排序取前 2-3 句
    key_sentences.sort(key=lambda x: -x[0])
    top = [s for _, s in key_sentences[:3]]

    if not top:
        # 没有明显的关键句，返回前 3 个有意义段落
        paragraphs = [p.strip() for p in full_text.split('\n') if len(p.strip()) > 30]
        top = paragraphs[:3]

    result = " ".join(top)
    if len(result) > 300:
        result = result[:297] + "..."
    return result
