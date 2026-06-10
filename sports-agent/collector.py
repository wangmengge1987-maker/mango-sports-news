# -*- coding: utf-8 -*-
"""RSS 新闻采集器"""

import feedparser
import hashlib
import requests
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Set
import config
import history


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
    # 过滤百度百家号等全部内容（百度 RSS 时间戳恒为今日，摘要结构不稳定，
    # 且可能存在有摘要但无日期的过期文章漏网）。懂球帝已覆盖中文体育新闻。
    link = entry.get("link", "")
    if link and ("baidu.com" in link or "baijiahao" in link):
        return False
    # 过滤不感兴趣的内容（中冠等）
    if _is_filtered_content(entry):
        return False
    # 硬性屏蔽已知过期文章（百度链接的已在上面拦掉，此处仅拦非百度源的）
    blocked_ids = getattr(config, "BLOCKED_ARTICLE_IDS", [])
    if blocked_ids and link:
        for bid in blocked_ids:
            if bid in link:
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
        # 先用 requests（支持超时）拉取，再交给 feedparser 解析
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

def _build_source_matchers():
    """为每类构建来源名匹配器（来源名精确匹配，不是子串）"""
    matchers = {}
    for cat, cfg in config.CATEGORIES.items():
        patterns = []
        for sp in cfg.get("source_priority", []):
            patterns.append(re.compile(re.escape(sp.lower())))
        matchers[cat] = patterns
    return matchers


def _is_filtered_content(entry: Dict[str, Any]) -> bool:
    """检查文章是否匹配过滤关键词（如中冠），匹配则丢弃"""
    filter_kws = getattr(config, "FILTER_KEYWORDS", [])
    if not filter_kws:
        return False
    text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
    for kw in filter_kws:
        if kw.lower() in text:
            return True
    return False


def classify(entries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """按关键词对新闻进行分类（支持来源名提示，避免交叉误配）"""
    result = {cat: [] for cat in config.CATEGORIES}
    result["其他"] = []
    patterns = _build_matchers()
    source_patterns = _build_source_matchers()

    for entry in entries:
        # Step 0: 过滤不感兴趣的内容（中冠等）
        if _is_filtered_content(entry):
            continue

        text = f"{entry['title']} {entry['summary']}".lower()
        source = entry.get("source", "").lower()

        # Step 1: 先尝试来源名匹配（来源名比关键词更可靠）
        # 检查来源名是否匹配某类的 source_priority
        source_matched_cat = None
        for cat in config.CATEGORIES:
            for pat in source_patterns.get(cat, []):
                if pat.search(source):
                    source_matched_cat = cat
                    break
            if source_matched_cat:
                break

        # Step 2: 关键词匹配
        matched_cat = None
        for cat in config.CATEGORIES:
            for pat in patterns[cat]:
                if pat.search(text):
                    matched_cat = cat
                    break
            if matched_cat:
                break

        # Step 3: 综合决策
        if source_matched_cat and matched_cat:
            # 来源和关键词都有匹配
            if source_matched_cat == matched_cat:
                # 一致 → 归入该类
                result[matched_cat].append(entry)
            else:
                # 不一致 → 检查关键词是否强匹配其他类别
                # 如果关键词强匹配（2个以上关键词命中），信任关键词
                # 否则保留来源分类
                if _is_strong_keyword_match(entry, matched_cat, patterns):
                    result[matched_cat].append(entry)  # 关键词强匹配 → 覆盖来源
                else:
                    result[source_matched_cat].append(entry)  # 来源更可靠
        elif source_matched_cat:
            result[source_matched_cat].append(entry)
        elif matched_cat:
            result[matched_cat].append(entry)
        else:
            result["其他"].append(entry)

    return result


def _is_strong_keyword_match(entry: Dict[str, Any], target_cat: str, patterns: dict) -> bool:
    """检查文章是否强匹配目标类别的关键词（多个关键词匹配视为强匹配）"""
    text = f"{entry['title']} {entry['summary']}".lower()
    match_count = 0
    for pat in patterns.get(target_cat, []):
        if pat.search(text):
            match_count += 1
    return match_count >= 2


def filter_recent(entries: List[Dict[str, Any]], window=config.TIME_WINDOW) -> List[Dict[str, Any]]:
    """只保留时间窗口内的新闻"""
    now = datetime.now(timezone.utc)
    return [e for e in entries if (now - e["published"]) <= window]


# 中文日期正则：匹配 "5月2日"、"5 月 2 日"、"5月2号"、"5.2" 等
_DATE_CN = re.compile(r'(\d{1,2})\s*[月.]\s*(\d{1,2})\s*[日号]')
# 英文日期正则：匹配 "May 2"、"May 2nd"、"2 May" 等（用于英文 RSS）
_EN_MONTHS = r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
_DATE_EN = re.compile(
    rf'(?:{_EN_MONTHS}\s+(\d{{1,2}})(?:st|nd|rd|th)?|'
    rf'(\d{{1,2}})\s+{_EN_MONTHS})',
    re.IGNORECASE,
)
_EN_MONTH_MAP = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'september': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12,
}


def _extract_date_from_text(text: str) -> tuple:
    """从文本中提取日期，返回 (month, day) 或 None"""
    if not text:
        return None
    # 匹配中文日期
    m = _DATE_CN.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    # 匹配英文日期
    m = _DATE_EN.search(text)
    if m:
        if m.group(1) and m.group(2):
            # "May 2" 格式
            month_str = m.group(1).lower()[:3]
            day = int(m.group(2))
        elif m.group(3) and m.group(4):
            # "2 May" 格式
            month_str = m.group(4).lower()[:3]
            day = int(m.group(3))
        else:
            return None
        month = _EN_MONTH_MAP.get(month_str)
        if month:
            return month, day
    return None


def filter_by_content_date(entries: List[Dict[str, Any]], max_age_days: int = 5) -> List[Dict[str, Any]]:
    """基于文章内容中的日期过滤过期新闻（针对 RSS 时间戳不可靠的情况）

    百度 RSS 的时间戳是 feed 生成时间而非文章发布时间，
    但中文新闻的标题或摘要开头常写 "5月2日，@NBA宣布..."
    这个日期才是真正的发布日期。

    改进：搜索全文而不仅是前 N 字符，同时支持中英文日期格式。
    """
    now = datetime.now(timezone.utc)
    result = []
    filtered = 0
    for e in entries:
        # 搜索完整标题和摘要（不截断），先剥离 HTML
        title = _strip_html_tags(e.get("title", ""))
        summary = _strip_html_tags(e.get("summary", ""))
        text = f"{title} {summary}"

        # 在完整文本中搜索日期（不限位置）
        date_found = _extract_date_from_text(text)

        if date_found:
            month, day = date_found
            try:
                article_date = datetime(now.year, month, day, tzinfo=timezone.utc)
                # 如果解析出的日期在未来（如12月出现在1月），可能跨年了
                if article_date > now:
                    article_date = datetime(now.year - 1, month, day, tzinfo=timezone.utc)
                age = (now - article_date).days
                if age > max_age_days:
                    filtered += 1
                    continue
            except ValueError:
                pass
        else:
            # No date found in content → 检查 RSS 时间戳是否明显过时
            pub = e.get("published")
            if pub:
                pub_age = (now - pub).days
                if pub_age > max_age_days:
                    filtered += 1
                    continue

        result.append(e)

    if filtered:
        print(f"[INFO] 内容日期过滤: 移除 {filtered} 条过期新闻（超过 {max_age_days} 天）")
    return result


def _content_hash(entry: Dict[str, Any]) -> str:
    """基于标题前80字生成哈希，用于跨源内容去重

    只使用标题（不用摘要），因为 RSS 摘要经常小幅变动导致哈希不稳定。
    同时去掉末尾的来源后缀（如 '- ESPN'）避免同文不同源误判。
    """
    title = _strip_html_tags(entry.get("title", "")).strip()[:80]
    # 去掉末尾的来源名称后缀（同一条新闻在不同源标题类似但后缀不同）
    title = re.sub(r'\s*[-–—|]\s*(ESPN|Yahoo|BBC|Sky Sports|The Guardian).*$', '', title, flags=re.IGNORECASE)
    key = title.lower().strip()
    if len(key) < 15:
        return None
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def filter_classified_after_translation(classified: Dict[str, List[Dict[str, Any]]], max_age_days: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    """翻译后按内容日期再次过滤

    translate_classified() 在标题/摘要中添加了 title_cn / summary_cn，
    此时中文文本中的"5月2日"等日期才可见。
    跑在 filter_by_content_date() 之后，补捉英文原文中不含日期的文章。
    """
    now = datetime.now(timezone.utc)
    filtered_total = 0
    result = {}
    for cat, items in classified.items():
        kept = []
        for item in items:
            cn_title = item.get("title_cn") or ""
            cn_summary = item.get("summary_cn") or ""
            text = f"{cn_title} {cn_summary}"

            date_found = _extract_date_from_text(text)
            if date_found:
                month, day = date_found
                try:
                    article_date = datetime(now.year, month, day, tzinfo=timezone.utc)
                    if article_date > now:
                        article_date = datetime(now.year - 1, month, day, tzinfo=timezone.utc)
                    age = (now - article_date).days
                    if age > max_age_days:
                        filtered_total += 1
                        continue
                except ValueError:
                    pass
            kept.append(item)
        if kept:
            result[cat] = kept
    if filtered_total:
        print(f"[INFO] 翻译后日期过滤: 移除 {filtered_total} 条含过期日期的新闻（> {max_age_days} 天前的内容）")
    return result


def collect_all(history_set: Set[str] = None, hash_history: Set[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """主入口：抓取所有源，过滤，分类，去重

    Args:
        history_set: URL 历史记录集合（跨日去重）
        hash_history: 内容哈希历史记录集合（相同文章不同 URL 去重）
    """
    all_entries = []
    for src in config.RSS_SOURCES:
        print(f"[INFO] 正在抓取: {src['name']} ({src['url']})")
        entries = fetch_rss(src["url"])
        for e in entries:
            e["source"] = src["name"]
            e["content_hash"] = _content_hash(e)
        all_entries.extend(entries)

    # 去重（按链接 + 按标题摘要哈希）
    seen_links = set()
    seen_hashes = set()
    unique = []
    for e in all_entries:
        # 链接去重
        if e["link"] and e["link"] in seen_links:
            continue
        seen_links.add(e["link"])
        # 内容哈希去重（相同文章不同 URL 的情况）
        ch = e.get("content_hash")
        if ch and ch in seen_hashes:
            continue
        seen_hashes.add(ch)
        unique.append(e)

    # 过滤24小时内
    recent = filter_recent(unique)
    print(f"[INFO] 去重后共 {len(unique)} 条，24小时内 {len(recent)} 条")

    # 补充内容日期过滤（针对百度 RSS 时间戳不可靠）
    recent = filter_by_content_date(recent)

    # 清洗：过滤视频类、劣质翻译等
    before = len(recent)
    recent = [e for e in recent if clean_entry(e)]
    if before - len(recent):
        print(f"[INFO] 清洗过滤: 移除 {before - len(recent)} 条低质量内容")

    # 分类
    classified = classify(recent)

    # 采集懂球帝（中文体育新闻）
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
                    e["content_hash"] = _content_hash(e)
                dq_all.extend(entries)
        # 去重（按链接）
        seen = set()
        dq_unique = []
        for e in dq_all:
            if e["link"] and e["link"] not in seen:
                seen.add(e["link"])
                dq_unique.append(e)
        # 懂球帝也进行 24h 时间过滤
        dq_recent = filter_recent(dq_unique)
        # 内容日期过滤（中文标题常含"5月2日"等，需检查）
        dq_recent = filter_by_content_date(dq_recent)
        print(f"[INFO] 懂球帝: 去重后 {len(dq_unique)} 条，24小时内 {len(dq_recent)} 条")
        if dq_recent:
            dq_classified = classify(dq_recent)
            print(f"[INFO] 懂球帝: 分类后 {sum(len(v) for v in dq_classified.values())} 条")
            for cat, items in dq_classified.items():
                if items:
                    classified.setdefault(cat, [])
                    classified[cat] = items + classified[cat]

    # 过滤已报道过的内容（跨日去重：URL + 内容哈希）
    if history_set:
        total_before = sum(len(v) for v in classified.values())
        filtered_classified = {}
        for cat in classified:
            filtered = history.filter_new(classified[cat], history_set)
            # 额外：按内容哈希过滤（不同 URL 相同内容）
            if hash_history:
                filtered = history.filter_new_by_hash(filtered, hash_history)
            if filtered:
                filtered_classified[cat] = filtered
        total_after = sum(len(v) for v in filtered_classified.values())
        filtered = total_before - total_after
        if filtered:
            # 判断是否为同一天重跑（同一天内不执行跨日去重）
            _same_day = False
            _lst = history.get_last_save_time()
            if _lst:
                _same_day = (datetime.now(timezone.utc).strftime("%Y-%m-%d") == _lst.strftime("%Y-%m-%d"))

            if _same_day:
                # 同一天重跑 → 保留全部内容（不跨日去重）
                print(f"[INFO] 跨日去重: 跳过 {filtered} 条（同一天重跑，保留全部 {total_before} 条）")
            elif total_after == 0:
                # 不同日期且全部在历史中 → RSS 返回了过期内容，清空
                print(f"[WARN] 跨日去重: 全部 {filtered} 条均为已报道旧闻，清空避免重复推送")
                classified = {cat: [] for cat in classified}
            else:
                print(f"[INFO] 跨日去重: 过滤 {filtered} 条已报道内容，保留 {total_after} 条新内容")
                classified = filtered_classified
    elif hash_history:
        # 没有 URL 历史但有哈希历史（初次启动场景）
        total_before = sum(len(v) for v in classified.values())
        filtered_classified = {}
        for cat in classified:
            filtered = history.filter_new_by_hash(classified[cat], hash_history)
            if filtered:
                filtered_classified[cat] = filtered
        total_after = sum(len(v) for v in filtered_classified.values())
        if total_after < total_before:
            print(f"[INFO] 内容哈希去重: 过滤 {total_before - total_after} 条已报道内容，保留 {total_after} 条新内容")
            if total_after > 0:
                classified = filtered_classified
            else:
                print(f"[WARN] 内容哈希去重: 全部均在历史中，保留当前内容（首次运行哈希去重）")

    return classified
