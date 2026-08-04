from flask import Flask, request, jsonify, Response
import requests
import os
import json

app = Flask(__name__)


NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "jamesjuhoon")
ORIGIN_API = os.environ.get("ORIGIN_API", "https://web-production-5c189.up.railway.app")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "Jh3k9xQw2mPv8LzT5nYc")


def send_ntfy(title, message, priority=3):
    headers = {"Title": title, "Priority": str(priority), "Tags": "mobile_phone"}
    try:
        resp = requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode("utf-8"), headers=headers, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print("ntfy error:", e)
        return False

def query_activity(days=1):
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    try:
        resp = requests.get(f"{ORIGIN_API}/activity/summary?days={days}", headers=headers, timeout=15)
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        return {"error": str(e)}


TOOLS = [
    {
        "name": "query_activity",
        "description": "查询用户过去N天的手机活动摘要",
        "inputSchema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "查询天数（默认1天）"}
            }
        }
    },
    {
        "name": "send_notification",
        "description": "给用户手机发送一条推送通知",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "通知标题"},
                "message": {"type": "string", "description": "通知内容"},
                "priority": {"type": "integer", "description": "优先级1-5，默认3"}
            },
            "required": ["title", "message"]
        }
    }
]

def make_response(req_id, result=None, error=None):
    resp = {"jsonrpc": "2.0", "id": req_id}
    if error:
        resp["error"] = error
    else:
        resp["result"] = result
    return resp

@app.route("/")
def index():
    return jsonify({"message": "AI Check MCP Server is running", "status": "ok"})

@app.route("/mcp", methods=["GET"])
def mcp_get():
    return jsonify({"message": "MCP endpoint ready. Use POST for JSON-RPC."})

@app.route("/mcp", methods=["POST"])
def mcp_post():
    body = request.get_json(silent=True) or {}
    method = body.get("method", "")
    req_id = body.get("id")
    accept = request.headers.get("Accept", "")

    result, error = None, None

    if method == "initialize":
        params = body.get("params", {})
        result = {
            "protocolVersion": params.get("protocolVersion", "2025-03-26"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "ai-check-mcp", "version": "1.0.0"}
        }
    elif method == "notifications/initialized":
        return Response(status=202)  
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = body.get("params", {})
        name = params.get("name", "")
        args = params.get("arguments", {})
        if name == "query_activity":
            days = int(args.get("days", 1))
            data = query_activity(days)
            result = {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}]}
        elif name == "send_notification":
            ok = send_ntfy(args.get("title", "通知"), args.get("message", ""), args.get("priority", 3))
            result = {"content": [{"type": "text", "text": "通知发送成功" if ok else "通知发送失败"}]}
        else:
            error = {"code": -32602, "message": f"未知工具: {name}"}
    else:
        error = {"code": -32601, "message": f"未知方法: {method}"}

    payload = make_response(req_id, result, error)

    
    if "text/event-stream" in accept:
        sse = f"event: message\ndata: {json.dumps(payload)}\n\n"
        return Response(sse, mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})

    return jsonify(payload)


handler = app
