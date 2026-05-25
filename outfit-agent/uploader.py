# -*- coding: utf-8 -*-
"""图床上传 — ImgURL"""

import os
import requests

import config


def upload_image(filepath: str) -> str | None:
    """上传图片到 ImgURL，返回公网 URL"""
    uid = config.IMGURL_UID
    token = config.IMGURL_TOKEN

    if not uid or not token:
        print("[WARN] 未配置 IMGURL_UID 或 IMGURL_TOKEN，跳过上传")
        return None

    if not os.path.exists(filepath):
        print(f"[WARN] 图片不存在: {filepath}")
        return None

    try:
        with open(filepath, "rb") as f:
            resp = requests.post(
                "https://www.imgurl.org/api/v2/upload",
                data={"uid": uid, "token": token},
                files={"file": f},
                timeout=30,
            )
        result = resp.json()
        if result.get("code") == 200:
            url = result["data"]["url"]
            print(f"[INFO] 图片上传成功: {url}")
            return url
        else:
            print(f"[WARN] 上传失败: {result.get('msg', '未知错误')}")
            return None
    except Exception as e:
        print(f"[ERROR] 上传异常: {e}")
        return None
