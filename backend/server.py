#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LobsterMC - 龙虾指挥中心后端"""
from flask import Flask, jsonify, send_from_directory, make_response
from datetime import datetime, timedelta
import json, os, sys

app = Flask(__name__, static_folder="../frontend", static_url_path="/static")

WORKSPACE       = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PORTFOLIO_FILE  = os.path.join(WORKSPACE, "paper_trading", "portfolio.json")
MONDAY_PLAN_FILE= os.path.join(WORKSPACE, "paper_trading", "monday_plan.json")
STATE_FILE      = os.path.join(WORKSPACE, "Star-Office-UI", "state.json")
ALPHAWHISPER_DIR= os.path.join(WORKSPACE, "AlphaWhisper")

# 注入 AlphaWhisper 路径
if ALPHAWHISPER_DIR not in sys.path:
    sys.path.insert(0, ALPHAWHISPER_DIR)

# ML 评分函数（懒加载，避免启动慢）
_ml_func = None
def _get_ml_func():
    global _ml_func
    if _ml_func is None:
        try:
            from radar_v2 import get_ml_score, ml_signal_grade, combined_decision
            _ml_func = (get_ml_score, ml_signal_grade, combined_decision)
        except Exception as e:
            print(f"[ML] 加载失败: {e}")
            _ml_func = False
    return _ml_func

# ML 分缓存（避免每次请求都抓行情）
_ml_cache = {}  # code -> (score, factors, grade, ts)
ML_CACHE_TTL = 300  # 5分钟

def get_ml_cached(code):
    """带缓存的 ML 评分"""
    now = datetime.now().timestamp()
    if code in _ml_cache:
        score, factors, grade, ts = _ml_cache[code]
        if now - ts < ML_CACHE_TTL:
            return score, factors, grade
    funcs = _get_ml_func()
    if not funcs:
        return None, {}, "N/A"
    get_ml_score, ml_signal_grade, _ = funcs
    score, factors = get_ml_score(code)
    grade, icon = ml_signal_grade(score)
    _ml_cache[code] = (score, factors, grade, now)
    return score, factors, grade

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

    # ── 持仓 ──
    p = rj(PORTFOLIO_FILE)
    if p:
        positions = p.get("持仓", {})
        active = {}
        for code, pos in positions.items():
            if pos.get("持仓数量", 0) > 0:
                cost  = pos.get("持仓成本", 0)
                close = pos.get("收盘价", cost)
                pnl   = round((close - cost) / cost * 100, 2) if cost else 0

                # ML 技术面评分
                ml_score, ml_factors, ml_grade = get_ml_cached(code)

                active[code] = {
                    "name":     pos.get("名称", code),
                    "shares":   pos.get("持仓数量"),
                    "cost":     cost,
                    "close":    close,
                    "pnl_pct":  pnl,
                    "score":    pos.get("信号分", 0),
                    "buy_date": pos.get("买入日期", ""),
                    "ml_score": ml_score,
                    "ml_grade": ml_grade,
                    "ml_vol_ratio": ml_factors.get("量比"),
                    "ml_mom5":      ml_factors.get("5日动量"),
                    "ml_rsi":       ml_factors.get("RSI14"),
                }

        total   = p.get("总资产", 0)
        initial = p.get("初始资金", 1000000)
        result["portfolio"] = {
            "cash":     p.get("cash", 0),
            "total":    total,
            "initial":  initial,
            "pnl_pct":  round((total - initial) / initial * 100, 2),
            "positions": active,
            "updated":  p.get("最后更新", ""),
        }

    # ── 信号 + 计划 + ML双因子决策 ──
    mp = rj(MONDAY_PLAN_FILE)
    if mp:
        funcs = _get_ml_func()
        plans = []
        for x in mp.get("plans", []):
            if x.get("status") != "PENDING":
                continue
            code = x.get("code", "")

            # ML 评分
            ml_score, ml_factors, ml_grade = get_ml_cached(code)

            # 双因子决策
            decision = ""
            if funcs:
                _, _, combined_decision = funcs
                kw_score = x.get("kw_score", 6)  # 默认6分
                sig_type = x.get("signal_type", "合作订单")
                decision = combined_decision(kw_score, ml_score, sig_type)

            plans.append({
                "code":      code,
                "name":      x.get("name"),
                "pct":       x.get("position_pct", 0),
                "ref":       x.get("ref_price", 0),
                "tp1":       x.get("tp1_price", 0),
                "sl":        x.get("stop_loss_price", 0),
                "desc":      x.get("signal_desc", ""),
                "ml_score":  ml_score,
                "ml_grade":  ml_grade,
                "ml_factors": {
                    "量比":   ml_factors.get("量比"),
                    "动量5":  ml_factors.get("5日动量"),
                    "RSI":    ml_factors.get("RSI14"),
                },
                "decision":  decision,
            })

        result["signal"] = {
            "id":       mp.get("signal", ""),
            "severity": mp.get("severity", ""),
            "summary":  mp.get("event_summary", [])[:4],
            "plans":    plans,
            "updated":  mp.get("last_updated", ""),
        }

    # ── Agent 状态 ──
    s = rj(STATE_FILE) or {}
    result["agent"] = {
        "state":   s.get("state", "idle"),
        "detail":  s.get("detail", "待命"),
        "updated": s.get("updated_at", ""),
    }

    return jsonify(result)

if __name__ == "__main__":
    print("LobsterMC running → http://127.0.0.1:19001")
    app.run(host="0.0.0.0", port=19001, debug=False)
