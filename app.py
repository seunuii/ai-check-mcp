from fastapi import FastAPI
app = FastAPI()
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
    try:
        r = requests.post(f"https://ntfy.sh/{NTFY_TOPIC}",
                          data=content.encode("utf-8"),
                          headers={"Title": title, "Priority": "high"},
                          timeout=10)
        return "推送成功" if r.status_code == 200 else f"推送失败：{r.status_code}"
    except Exception as e:
        return f"推送异常：{e}"

TOOLS = [
    {"name": "check_on_wife", "description": "查岗老婆的手机活动",
     "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}}}},
    {"name": "ntfy_alert", "description": "给老婆手机发推送弹窗",
     "inputSchema": {"type": "object", "properties": {
         "title": {"type": "string"}, "content": {"type": "string"}},
         "required": ["content"]}}
]

FUNCS = {"check_on_wife": check_on_wife, "ntfy_alert": ntfy_alert}

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_
