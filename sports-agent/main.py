# -*- coding: utf-8 -*-
"""Mango 体育简报生成器 — 主入口

用法:
    python main.py                  # 生成今日简报
    python main.py --push           # 生成并推送到微信
    python main.py --push-only      # 仅推送已有简报（不重新生成）
    python main.py --date 2026-05-13        # 指定日期
    python main.py --force          # 覆盖已有文件
"""

import argparse
import os
import re
import sys
from datetime import datetime

from collector import collect_all, filter_classified_after_translation
from scores import collect_scores
from generator import generate_md, generate_push_text, save_md
from pusher import push_to_wechat
from translator import batch_translate, translate_classified
from history import (
    load_history, save_history, prune_history, reset_history,
    load_hash_history, save_hash_history, prune_hash_history,
)
import config


_REVIEW_PATTERNS = [
    # 列表类标题但没有具体内容
    (r'\d+\s*(件事|个问题|个看点|things|ways|reasons|to watch)', "列表类标题缺少具体内容"),
    # 手术/医疗新闻缺少病因说明
    (r'(手术|surgery|transplant|移植|heart)', "医疗类新闻 — 检查是否说明了病因/背景"),
    # 标题太短（可能是劣质翻译）
    (r'^.{1,15}$', "标题过短，可能信息不足"),
]


def _review_push_content(push_text: str) -> list:
    """推送前质量检查：找出不清晰、需要补充的内容"""
    notes = []
    for line in push_text.split('\n'):
        line = line.strip()
        # 跳过非内容行
        if not line.startswith('- ') and not line.startswith('  - '):
            continue
        content = line.lstrip('- ').strip()
        if not content:
            continue
        for pattern, msg in _REVIEW_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                # 检查是否已经有完整上下文（含 full_context）
                if "——" not in content:
                    notes.append(f"[{msg}] {content[:60]}...")
    return notes


def main():
    parser = argparse.ArgumentParser(description="Mango 体育新闻简报生成器")
    parser.add_argument("--date", type=str, default=None, help="指定日期 (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true", help="强制覆盖已有文件")
    parser.add_argument("--push", action="store_true", help="生成后推送到微信")
    parser.add_argument("--push-only", action="store_true", help="仅推送已有简报，不重新生成")
    parser.add_argument("--reset-history", action="store_true", help="清空文章历史记录")
    args = parser.parse_args()

    # ── 清空历史模式 ────────────────────────────────────────
    if args.reset_history:
        url_count = reset_history()
        print(f"[INFO] 已清空文章 URL 历史记录（{url_count} 条）")
        # 也清空内容哈希历史
        import os as _os
        hash_file = _os.path.join("output", ".content_hash_history.json")
        if _os.path.exists(hash_file):
            _os.remove(hash_file)
            print(f"[INFO] 已清空内容哈希历史记录")
        return 0

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join("output", f"{date_str}-今日体育简报.md")
    push_title = f"今日体育简报 ({date_str})"

    # ── 仅推送模式 ──────────────────────────────────────
    if args.push_only:
        if not os.path.exists(filepath):
            print(f"[ERROR] 简报不存在: {filepath}")
            print("[INFO] 请先运行 python main.py 生成简报")
            return 1
        with open(filepath, "r", encoding="utf-8") as f:
            md_content = f.read()
        push_to_wechat(push_title, md_content)
        return 0

    # ── 检查是否有缓存 ──────────────────────────────────
    if os.path.exists(filepath) and not args.force:
        print(f"[INFO] 简报已存在: {filepath}")
        if args.push:
            print("[INFO] --push 已指定，将推送已有简报")
            with open(filepath, "r", encoding="utf-8") as f:
                md_content = f.read()
            push_to_wechat(push_title, md_content)
        else:
            print("[INFO] 跳过（使用 --force 强制重新生成）")
        return 0

    # ── 主流程 ──────────────────────────────────────────
    print("=" * 50)
    print("  Mango 体育新闻简报生成器")
    print(f"  日期: {date_str}")
    print("=" * 50)

    # 1. 采集 RSS 新闻
    print("\n[Step 1/5] 采集新闻...")
    history_set = load_history()
    if history_set:
        print(f"[INFO] 已加载 {len(history_set)} 条历史 URL 记录")
    hash_history = load_hash_history()
    if hash_history:
        print(f"[INFO] 已加载 {len(hash_history)} 条内容哈希记录，将过滤重复内容")
    classified = collect_all(history_set=history_set, hash_history=hash_history)

    # 2. 翻译新闻
    print("\n[Step 2/5] 翻译新闻...")
    translate_classified(classified)

    # 2.5 翻译后日期过滤（补捉中文标题中的"5月2日"等原文不含的日期）
    classified = filter_classified_after_translation(classified)

    # 3. 补充文章全文（对摘要不清晰的条目，读懂背景后再总结）
    print("\n[Step 3/5] 补充文章全文背景...")
    from article_reader import needs_full_text, get_context_summary
    fetch_count = 0
    for items in classified.values():
        for item in items:
            if needs_full_text(item) and fetch_count < 8:
                context = get_context_summary(item)
                if context:
                    item["full_context"] = context
                    fetch_count += 1
                    print(f"  [OK] {item.get('source','?')}: {context[:50]}...")
    if fetch_count == 0:
        print("  [INFO] 全部条目摘要已足够，无需补充")

    # 4. 采集比分（含球员表现数据）
    print("\n[Step 4/5] 采集比分及球员数据...")
    scores = collect_scores()

    # 5. 生成简报
    print("\n[Step 5/5] 生成简报...")
    md_content = generate_md(classified, scores)
    saved_path = save_md(md_content, date_str)

    # 6. 保存文章历史（跨日去重用）
    all_urls = set()
    all_hashes = set()
    for items in classified.values():
        for item in items:
            if item.get("link"):
                all_urls.add(item["link"])
            ch = item.get("content_hash")
            if ch:
                all_hashes.add(ch)
    if all_urls:
        save_history(all_urls)
        pruned = prune_history(days=config.HISTORY_PRUNE_DAYS)
        if pruned:
            print(f"[INFO] 清理了 {pruned} 条过期 URL 历史记录")
    if all_hashes:
        save_hash_history(all_hashes)
        pruned_hash = prune_hash_history(days=45)
        if pruned_hash:
            print(f"[INFO] 清理了 {pruned_hash} 条过期内容哈希记录")

    # 4. 推送前 Review
    print("\n[Review] 检查简报质量...")
    push_text = generate_push_text(classified, scores)
    review_notes = _review_push_content(push_text)
    if review_notes:
        for note in review_notes:
            print(f"  [!] {note}")
    else:
        print("  [OK] 简报内容清晰，无需调整")

    # 5. 推送
    if args.push:
        print("\n[推送] 正在发送到微信...")
        push_to_wechat(push_title, push_text)
    else:
        print("\n[INFO] 未指定 --push，跳过推送")
        print("[INFO] 推送用法: python main.py --push")
        print(f"[INFO] 或编辑 run.bat 添加 --push 参数")

    print(f"\n[完成] 简报已保存至: {saved_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
