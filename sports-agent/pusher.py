# -*- coding: utf-8 -*-
"""微信推送 — 支持 PushPlus（主）和 Server酱（备选）"""

import os
import requests

import config


def _load_env():
    """从 .env 文件加载环境变量（如有）"""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


_load_env()


def push_to_wechat(title: str, content: str) -> bool:
    """推送到微信（PushPlus），返回是否成功"""
    token = config.PUSHPLUS_TOKEN or os.environ.get("PUSHPLUS_TOKEN", "")

    if not token:
        print("[WARN] 未配置 PUSHPLUS_TOKEN，跳过推送")
        print(f"[INFO] 请注册 https://www.pushplus.plus 获取 Token")
        print(f"[INFO] 可设置环境变量 PUSHPLUS_TOKEN 或在 config.py 中配置")
        return False

    # 截断过长的内容
    if len(content) > config.MAX_PUSH_LENGTH:
        content = content[:config.MAX_PUSH_LENGTH] + "\n\n... (内容过长已截断)"

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
            print("[INFO] 推送成功 [OK]")
            return True
        else:
            print(f"[WARN] 推送失败: {result.get('msg', '未知错误')}")
            return False
    except Exception as e:
        print(f"[ERROR] 推送异常: {e}")
        return False


def push_via_serverchan(title: str, content: str, send_key: str = "") -> bool:
    """备选方案：通过 Server酱 推送"""
    key = send_key or os.environ.get("SERVERCHAN_KEY", "")
    if not key:
        print("[WARN] 未配置 SERVERCHAN_KEY，跳过 Server酱 推送")
        return False

    # Server酱 markdown 模式
    payload = {"title": title, "desp": content}
    try:
        resp = requests.post(
            f"https://sctapi.ftqq.com/{key}.send",
            data=payload,
            timeout=15,
        )
        result = resp.json()
        if result.get("code") == 0:
            print("[INFO] Server酱 推送成功 [OK]")
            return True
        else:
            print(f"[WARN] Server酱 推送失败: {result.get('message', '未知错误')}")
            return False
    except Exception as e:
        print(f"[ERROR] Server酱 推送异常: {e}")
        return False
