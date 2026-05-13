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
import sys
from datetime import datetime

from collector import collect_all
from scores import collect_scores
from generator import generate_md, generate_push_text, save_md
from pusher import push_to_wechat


def main():
    parser = argparse.ArgumentParser(description="Mango 体育新闻简报生成器")
    parser.add_argument("--date", type=str, default=None, help="指定日期 (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true", help="强制覆盖已有文件")
    parser.add_argument("--push", action="store_true", help="生成后推送到微信")
    parser.add_argument("--push-only", action="store_true", help="仅推送已有简报，不重新生成")
    args = parser.parse_args()

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
    print("\n[Step 1/3] 采集新闻...")
    classified = collect_all()

    # 2. 采集比分
    print("\n[Step 2/3] 采集比分...")
    scores = collect_scores()

    # 3. 生成简报
    print("\n[Step 3/3] 生成简报...")
    md_content = generate_md(classified, scores)
    saved_path = save_md(md_content, date_str)

    # 4. 推送
    if args.push:
        print("\n[推送] 正在发送到微信...")
        push_text = generate_push_text(classified, scores)
        push_to_wechat(push_title, push_text)
    else:
        print("\n[INFO] 未指定 --push，跳过推送")
        print("[INFO] 推送用法: python main.py --push")
        print(f"[INFO] 或编辑 run.bat 添加 --push 参数")

    print(f"\n[完成] 简报已保存至: {saved_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
