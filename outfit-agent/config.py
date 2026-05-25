# -*- coding: utf-8 -*-
"""穿搭助手 — 配置"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")
IMGURL_UID = os.getenv("IMGURL_UID", "")
IMGURL_TOKEN = os.getenv("IMGURL_TOKEN", "")

# ── 城市 ──
CITY = os.getenv("CITY", "广州")

# ── 路径 ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ABOUTME_PATH = os.path.join(BASE_DIR, "aboutme.md")

# ── 推送 ──
MAX_PUSH_LENGTH = 40000

# ── API 地址 ──
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
STABILITY_API_URL = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
