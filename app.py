import json, os, requests
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

JST = timedelta(hours=9)
ORIGIN = os.environ.get("ORIGIN_API", "https://web-production-5c189.up.railway.app")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "jamesjuhoon")

def check_on_wife(limit=10):
    try:
        r = requests.get(f"{ORIGIN}/activity/summary", timeout=10)
        data = r.json()
    except Exception as e:
        return f"查岗失败：{e}"
    apps = data.get("recent_apps", [])
    ses = data.get("sessions", {})
    lines = [f"最近打开：{', '.join(apps)}" if apps else "暂无记录"]
    if ses:
        for app, secs in sorted(ses.items(), key=lambda x: x[1], reverse=True):
            m, s = divmod(secs, 60)
            lines.append(f"  {app}: {m}分{s}秒")
    return "\n".join(lines)

def ntfy_alert(title="查岗", content=""):
    if not content:
        return "内容不能为空"
    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    try:
        r = requests.post(url,
