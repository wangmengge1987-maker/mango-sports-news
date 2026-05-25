# -*- coding: utf-8 -*-
"""穿搭建议生成 — 调用 DeepSeek API"""

import json
import os
import requests

import config


def read_aboutme() -> str:
    """读取个人风格档案"""
    if os.path.exists(config.ABOUTME_PATH):
        with open(config.ABOUTME_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "（用户未提供风格档案）"


def generate_advice(occasion: str, people: str, weather: dict) -> dict:
    """根据场合、见谁、天气，生成穿搭建议

    Returns:
        dict: {
            "analysis": "...
            "outfit": {
                "tops": "...",
                "bottoms": "...",
                "shoes": "...",
                "accessories": "...",
            },
            "summary": "...",
            "image_prompt": "用于生图的英文 prompt"
        }
    """
    style = read_aboutme()

    system_prompt = """你是专业的个人形象穿搭顾问，擅长根据场合、天气和个人风格给出实用搭配建议。

你需要输出 JSON 格式的结果，包含：
- analysis: 对场合、天气、风格的简要分析
- outfit: 穿搭方案（tops, bottoms, shoes, accessories 四个字段）
- summary: 一句话总结推荐
- image_prompt: 一句英文描述，用于 AI 生图，描述一个人穿着这套搭配的样子

要求：
1. 建议要具体到单品，比如"白色亚麻衬衫"而不是"浅色上衣"
2. 色彩搭配要协调
3. 结合 weather 里的温度、天气状况
4. 参考用户的风格档案做个性化
5. image_prompt 用英文，中景或半身展示穿搭，不要用 full body 避免变形。描述人物体型、肤色、穿搭细节
6. 只输出 JSON，不要多余的文字"""

    user_prompt = f"""【场合】{occasion}
【见什么人】{people}
【天气】{json.dumps(weather, ensure_ascii=False)}
【我的风格】{style}"""

    if not config.DEEPSEEK_API_KEY:
        return _fallback_advice(occasion, people, weather)

    try:
        resp = requests.post(
            config.DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
            },
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        content = result["choices"][0]["message"]["content"]

        # 解析 JSON
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        if content.startswith("json"):
            content = content[4:].strip()

        advice = json.loads(content)
        return advice

    except Exception as e:
        print(f"[WARN] AI 建议生成失败: {e}")
        return _fallback_advice(occasion, people, weather)


def _fallback_advice(occasion: str, people: str, weather: dict) -> dict:
    """API 不可用时的本地兜底"""
    temp = weather.get("temp", "25°C")
    condition = weather.get("condition", "晴")
    return {
        "analysis": f"今天{weather.get('city', '当地')}{condition}，气温{temp}。场合：{occasion}，见{people}。",
        "outfit": {
            "tops": "纯色棉质T恤 / 轻薄衬衫（根据温度选择）",
            "bottoms": "直筒休闲裤或合身牛仔裤",
            "shoes": "白色运动鞋或乐福鞋",
            "accessories": "简约手表，帆布托特包",
        },
        "summary": f"今日{occasion}穿搭推荐：简约得体，以舒适为主。",
        "image_prompt": f"A fashionable person wearing casual outfit, suitable for {occasion}, {condition} weather {temp}, full body shot, studio lighting, fashion photography style.",
    }
