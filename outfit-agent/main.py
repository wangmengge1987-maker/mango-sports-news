# -*- coding: utf-8 -*-
"""穿搭助手 — 主入口"""

import os
import sys
from datetime import datetime

# 强制 stdout 使用 UTF-8（解决 Windows GBK 终端 emoji 报错）
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from weather import get_weather
from advisor import generate_advice
from image_gen import generate_image
from uploader import upload_image
from pusher import push_to_wechat
import config


def main():
    auto_mode = "--auto" in sys.argv or "-a" in sys.argv

    print("=" * 50)
    print("  \U0001f455 穿搭助手 v1.0")
    print("=" * 50)

    # ── Step 1: 问场合 ──
    if auto_mode:
        weekday = datetime.now().weekday()
        if weekday < 5:  # Mon-Fri
            occasion = "上班"
            people = "同事和客户"
        else:  # Sat-Sun
            occasion = "日常"
            people = "自己"
        print(f"\n[自动模式] 场合: {occasion}, 会见: {people}")
    else:
        print("\n早上好！今天我来帮你搭配 \U0001f60a")
        occasion = input("今天去什么场合？（上班 / 面试 / 约会 / 运动 / 日常等）: ").strip()
        people = input("会见什么人？（客户 / 朋友 / 同事 / 自己等）: ").strip()

    # ── Step 2: 查天气 ──
    print(f"\n[1/5] 正在查询 {config.CITY} 天气...")
    weather = get_weather()
    print(f"  \U0001f3d8  {weather.get('description', '')}")

    # ── Step 3: AI 穿搭建议 ──
    print(f"\n[2/5] AI 正在分析穿搭建议...")
    advice = generate_advice(occasion, people, weather)

    outfit = advice.get("outfit", {})
    analysis = advice.get("analysis", "")
    summary = advice.get("summary", "")
    image_prompt = advice.get("image_prompt", "")

    print(f"\n  \U0001f9d5 分析：{analysis}")
    print(f"  \U0001f455 上装：{outfit.get('tops', '')}")
    print(f"  \U0001f456 下装：{outfit.get('bottoms', '')}")
    print(f"  \U0001f45f 鞋子：{outfit.get('shoes', '')}")
    print(f"  \U0001f4f1 配饰：{outfit.get('accessories', '')}")
    print(f"  ✨ 总结：{summary}")

    # ── Step 4: 生成图片 ──
    print(f"\n[3/5] 正在生成穿搭效果图...")
    image_path = generate_image(image_prompt)
    image_url = None

    # ── Step 5: 上传图片到图床 ──
    if image_path:
        print(f"\n[4/5] 上传图片到图床...")
        image_url = upload_image(image_path)

    # ── Step 6: 保存 md 文档 ──
    print(f"\n[5/5] 保存穿搭文档...")
    md_path = _save_md(occasion, people, weather, advice, image_url or image_path)
    print(f"  \U0001f4c4 已保存: {md_path}")

    # ── Step 7: 推送微信 ──
    if config.PUSHPLUS_TOKEN:
        print(f"\n[\U0001f514] 推送微信...")
        md_for_push = _build_push_content(occasion, weather, advice, image_url)
        push_to_wechat(f"今日穿搭建议 ({datetime.now().strftime('%Y-%m-%d')})", md_for_push)
    else:
        print(f"\n[INFO] 未配置 PUSHPLUS_TOKEN，跳过微信推送")

    print(f"\n{'=' * 50}")
    print(f"  ✅ 今日穿搭已完成！")
    print(f"{'=' * 50}")


def _save_md(occasion: str, people: str, weather: dict, advice: dict, image_path: str | None) -> str:
    """保存穿搭文档到 output/"""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(config.OUTPUT_DIR, f"{date_str}-今日穿搭.md")

    outfit = advice.get("outfit", {})
    analysis = advice.get("analysis", "")
    summary = advice.get("summary", "")

    lines = [
        f"# 今日穿搭 ({date_str})",
        "",
        f"## 今日行程",
        f"- **场合**：{occasion}",
        f"- **会见**：{people}",
        "",
        f"## 天气",
        f"- **城市**：{weather.get('city', '')}",
        f"- **天气**：{weather.get('description', '')}",
        "",
        f"## \U0001f9d5 穿搭分析",
        analysis,
        "",
        f"## \U0001f455 推荐搭配",
        f"| 类别 | 建议 |",
        "|------|------|",
        f"| 上装 | {outfit.get('tops', '')} |",
        f"| 下装 | {outfit.get('bottoms', '')} |",
        f"| 鞋子 | {outfit.get('shoes', '')} |",
        f"| 配饰 | {outfit.get('accessories', '')} |",
        "",
        f"## ✨ 总结",
        summary,
        "",
    ]

    if image_path and os.path.exists(image_path):
        lines.append(f"## \U0001f5bc 穿搭效果图")
        lines.append(f"![穿搭效果图]({image_path})")
        lines.append("")

    lines.append("---")
    lines.append(f"*由穿搭助手自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append("")

    content = "\n".join(lines)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


def _build_push_content(occasion: str, weather: dict, advice: dict, image_url: str | None) -> str:
    """构造微信推送内容"""
    outfit = advice.get("outfit", {})
    summary = advice.get("summary", "")

    lines = [
        f"**今日行程**：{occasion}",
        f"**天气**：{weather.get('description', '')}",
        "",
        "**推荐搭配**",
        f"- 上装：{outfit.get('tops', '')}",
        f"- 下装：{outfit.get('bottoms', '')}",
        f"- 鞋子：{outfit.get('shoes', '')}",
        f"- 配饰：{outfit.get('accessories', '')}",
        "",
        f"**{summary}**",
    ]

    if image_url:
        lines.append("")
        lines.append(f"![穿搭效果]({image_url})")

    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
