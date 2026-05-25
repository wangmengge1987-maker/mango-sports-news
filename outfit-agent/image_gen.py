# -*- coding: utf-8 -*-
"""穿搭图片生成 — 使用 Pollinations.ai（免费，无需 API Key）"""

import os
import urllib.parse
import requests

import config


def generate_image(prompt: str, outfit_dir: str = None) -> str | None:
    """根据英文 prompt 生成穿搭图片"""
    output_dir = outfit_dir or config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    # 精心构造的 prompt：避免全身变形，采用中景展示穿搭
    enhanced_prompt = (
        f"{prompt}, fashion photography, well-fitted clothes, "
        f"normal body proportions, mid shot, standing, "
        f"solid color background, studio lighting, sharp focus, high quality"
    )

    # 固定 seed 保证一致性，使用 flux-realism 模型减少变形
    image_url = (
        f"https://image.pollinations.ai/prompt/"
        f"{urllib.parse.quote(enhanced_prompt)}"
        f"?width=864&height=1152&model=flux-realism&seed=42"
    )

    try:
        print(f"[INFO] 正在生成穿搭图片...")
        resp = requests.get(image_url, timeout=120)
        resp.raise_for_status()

        filepath = os.path.join(output_dir, "outfit.png")
        with open(filepath, "wb") as f:
            f.write(resp.content)

        print(f"[INFO] 图片已保存: {filepath} ({len(resp.content) / 1024:.0f} KB)")
        return filepath

    except Exception as e:
        print(f"[WARN] 图片生成失败: {e}")
        # 降级到基础模型再试一次
        try:
            fallback_url = (
                f"https://image.pollinations.ai/prompt/"
                f"{urllib.parse.quote(enhanced_prompt)}"
                f"?width=768&height=1024&model=flux"
            )
            resp = requests.get(fallback_url, timeout=120)
            resp.raise_for_status()
            filepath = os.path.join(output_dir, "outfit.png")
            with open(filepath, "wb") as f:
                f.write(resp.content)
            print(f"[INFO] 图片已保存 (降级): {filepath}")
            return filepath
        except Exception as e2:
            print(f"[WARN] 降级也失败: {e2}")
            return None
