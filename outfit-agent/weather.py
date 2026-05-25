# -*- coding: utf-8 -*-
"""天气查询 — 使用 wttr.in（免费，无需 API Key）"""

import json
import requests

import config


def get_weather(city: str = None) -> dict:
    """获取指定城市的当前天气和今日预报

    Returns:
        dict: {
            "city": "广州",
            "temp": "28°C",
            "condition": "多云",
            "humidity": "65%",
            "wind": "10 km/h",
            "high": "32°C",
            "low": "24°C",
            "description": "全天多云，气温24-32°C，东南风2级"
        }
    """
    city = city or config.CITY
    url = f"https://wttr.in/{city}?format=j1&lang=zh"

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[WARN] 天气查询失败: {e}")
        return {
            "city": city,
            "temp": "N/A",
            "condition": "未知",
            "description": f"无法获取{city}天气数据",
        }

    try:
        current = data["current_condition"][0]
        forecast = data["weather"][0]

        result = {
            "city": city,
            "temp": f"{current['temp_C']}°C",
            "condition": current["weatherDesc"][0]["value"],
            "humidity": f"{current['humidity']}%",
            "wind": current["windspeedKmph"] + " km/h",
            "high": f"{forecast['maxtempC']}°C",
            "low": f"{forecast['mintempC']}°C",
            "description": _build_description(current, forecast),
        }
        return result
    except (KeyError, IndexError) as e:
        print(f"[WARN] 天气数据解析失败: {e}")
        return {"city": city, "temp": "N/A", "condition": "未知", "description": f"解析{city}天气失败"}


def _build_description(current: dict, forecast: dict) -> str:
    """生成一段自然的中文天气描述"""
    temp = current["temp_C"]
    condition_en = current["weatherDesc"][0]["value"]
    high = forecast["maxtempC"]
    low = forecast["mintempC"]
    humidity = current["humidity"]
    wind = current["windspeedKmph"]
    return f"{condition_en}，气温{low}-{high}°C，当前{temp}°C，湿度{humidity}%，风速{wind}km/h"
