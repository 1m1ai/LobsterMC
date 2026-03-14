#!/usr/bin/env python3
"""LobsterMC - 龙虾指挥中心后端"""
from flask import Flask, jsonify, send_from_directory, make_response
from datetime import datetime
import json, os

app = Flask(__name__, static_folder="../frontend", static_url_path="/static")

WORKSPACE = os.path.join(os.path.dirname(__file__), "..", "..", )
PORTFOLIO_FILE = os.path.join(WORKSPACE, "paper_trading", "portfolio.json")
MONDAY_PLAN_FILE = os.path.join(WORKSPACE, "paper_trading", "monday_plan.json")
STATE_FILE = os.path.join(WORKSPACE, "Star-Office-UI", "state.json")

def rj(path):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except: pass
    return None

@app.after_request
def no_cache(r):
    if not r.content_type.startswith("image"):
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return r

@app.route("/")
def index():
    path = os.path.join(os.path.dirname(__file__), "../frontend/index.html")
    with open(path, "r", encoding="utf-8") as f:
        return make_response(f.read(), 200, {"Content-Type": "text/html"})

@app.route("/api/status")
def api_status():
    result = {"ok": True, "ts": datetime.now().isoformat()}

    # 持仓
    p = rj(PORTFOLIO_FILE)
    if p:
        positions = p.get("持仓", {})
        active = {}
        for code, pos in positions.items():
            if pos.get("持仓数量", 0) > 0:
                cost = pos.get("持仓成本", 0)
                close = pos.get("收盘价", cost)
                pnl = round((close - cost) / cost * 100, 2) if cost else 0
                active[code] = {
                    "name": pos.get("名称", code), "shares": pos.get("持仓数量"),
                    "cost": cost, "close": close, "pnl_pct": pnl,
                    "score": pos.get("信号分", 0), "buy_date": pos.get("买入日期", "")
                }
        total = p.get("总资产", 0); initial = p.get("初始资金", 1000000)
        result["portfolio"] = {
            "cash": p.get("cash", 0), "total": total, "initial": initial,
            "pnl_pct": round((total - initial) / initial * 100, 2),
            "positions": active, "updated": p.get("最后更新", "")
        }

    # 信号
    mp = rj(MONDAY_PLAN_FILE)
    if mp:
        plans = [{"code": x.get("code"), "name": x.get("name"), "pct": x.get("position_pct", 0),
                  "ref": x.get("ref_price", 0), "tp1": x.get("tp1_price", 0),
                  "sl": x.get("stop_loss_price", 0), "desc": x.get("signal_desc", "")}
                 for x in mp.get("plans", []) if x.get("status") == "PENDING"]
        result["signal"] = {
            "id": mp.get("signal", ""), "severity": mp.get("severity", ""),
            "summary": mp.get("event_summary", [])[:4], "plans": plans,
            "updated": mp.get("last_updated", "")
        }

    # Agent状态
    s = rj(STATE_FILE) or {}
    result["agent"] = {"state": s.get("state", "idle"), "detail": s.get("detail", "待命"), "updated": s.get("updated_at", "")}

    return jsonify(result)

if __name__ == "__main__":
    print("LobsterMC running → http://127.0.0.1:19001")
    app.run(host="0.0.0.0", port=19001, debug=False)
