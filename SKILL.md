# LobsterMC — AI Trading Command Center

## Overview
LobsterMC is a cyberpunk-styled AI agent dashboard with live trading intelligence. 
It combines agent fleet monitoring with a 3-layer trading signal system, portfolio tracking, and execution planning — all in a single zero-dependency web interface.

Activate when the user asks to:
- Start or launch LobsterMC
- View their agent fleet dashboard
- Check trading signals or portfolio
- See the command center

## Prerequisites
- Python 3.10+ with Flask (`pip install flask`)
- OpenClaw workspace at `~/.openclaw/workspace`

## Launch

```powershell
$py = "C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe"
$env:PYTHONUTF8 = 1
# Kill any existing instance
Stop-Process -Name python -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
# Start
Start-Process -FilePath $py -ArgumentList "server.py" `
  -WorkingDirectory "$env:USERPROFILE\.openclaw\workspace\LobsterMC\backend" `
  -WindowStyle Hidden
Start-Sleep -Seconds 3
# Verify
Invoke-WebRequest -Uri "http://127.0.0.1:19001/api/status" -UseBasicParsing | Select-Object StatusCode
```

Then open: **http://127.0.0.1:19001**

## Data Files (optional)

LobsterMC auto-reads these files if they exist:

| File | Content |
|------|---------|
| `paper_trading/portfolio.json` | Holdings, P&L, cash |
| `paper_trading/monday_plan.json` | Pending buy orders |
| `Star-Office-UI/state.json` | Current agent state |

## Port
Default: `19001`

## Project Structure
```
LobsterMC/
├── SKILL.md            ← this file
├── README.md           ← full documentation
├── backend/
│   └── server.py       ← Flask API
└── frontend/
    └── index.html      ← Single-file SPA
```

## Stop

```powershell
# Find and kill the Flask process on port 19001
$p = Get-NetTCPConnection -LocalPort 19001 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($p) { Stop-Process -Id $p.OwningProcess -Force }
```

## Notes
- No npm, no webpack, no build step required
- Single HTML file frontend with embedded Canvas particle system
- Auto-refreshes every 30 seconds
- Works without any data files (shows empty state gracefully)
