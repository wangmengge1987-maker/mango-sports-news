# -*- coding: utf-8 -*-
"""微信推送 — PushPlus"""

import os
import requests

import config


def push_to_wechat(title: str, content: str) -> bool:
    """推送到微信（PushPlus）"""
    token = config.PUSHPLUS_TOKEN or os.environ.get("PUSHPLUS_TOKEN", "")
    if not token:
        print("[WARN] 未配置 PUSHPLUS_TOKEN，跳过推送")
        return False

    if len(content) > config.MAX_PUSH_LENGTH:
        content = content[: config.MAX_PUSH_LENGTH] + "\n\n...（内容过长已截断）"

    payload = {
        "token": token,
        "title": title,
        "content": content,
        "template": "markdown",
    }

    try:
        resp = requests.post(
            "https://www.pushplus.plus/send",
            json=payload,
            timeout=15,
        )
        result = resp.json()
        if result.get("code") == 200:
            print("[INFO] 微信推送成功")
            return True
        else:
            print(f"[WARN] 推送失败: {result.get('msg', '未知错误')}")
            return False
    except Exception as e:
        print(f"[ERROR] 推送异常: {e}")
        return False
