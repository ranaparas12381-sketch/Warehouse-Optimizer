from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent
WAREHOUSE_ROOT = PROJECT_ROOT / "warehouse_openenv"
if str(WAREHOUSE_ROOT) not in sys.path:
    sys.path.insert(0, str(WAREHOUSE_ROOT))

from env.models import ActionModel, ObservationModel  # noqa: E402
from env.warehouse_env import WarehouseEnv  # noqa: E402
from tasks.easy import make_config as make_easy_config  # noqa: E402
from tasks.hard import make_config as make_hard_config  # noqa: E402
from tasks.medium import make_config as make_medium_config  # noqa: E402


TASK_FACTORIES = {
    "easy": make_easy_config,
    "medium": make_medium_config,
    "hard": make_hard_config,
}


class ResetRequest(BaseModel):
    task: str = Field(default="medium")
    seed: Optional[int] = Field(default=None)


class StepRequest(BaseModel):
    session_id: Optional[str] = Field(default=None)
    action: Optional[Dict[str, Any] | list[int]] = Field(default=None)
    order_quantities: Optional[list[int]] = Field(default=None)


class StateRequest(BaseModel):
    session_id: Optional[str] = Field(default=None)


class EnvSession:
    def __init__(self, env: WarehouseEnv, task: str):
        self.env = env
        self.task = task


app = FastAPI(title="Warehouse Optimization OpenEnv Server", version="1.0.0")
SESSIONS: Dict[str, EnvSession] = {}
DEFAULT_SESSION_ID = "default"


def _build_env(task: str) -> WarehouseEnv:
    normalized = task.lower()
    if normalized not in TASK_FACTORIES:
        raise HTTPException(status_code=400, detail=f"Unsupported task '{task}'. Choose from easy, medium, hard.")
    return WarehouseEnv(TASK_FACTORIES[normalized]())


def _serialize_observation(observation: ObservationModel) -> Dict[str, Any]:
    return observation.model_dump()


def _serialize_state(env: WarehouseEnv, session_id: str, task: str) -> Dict[str, Any]:
    state = env.state().model_dump()
    return {
        "session_id": session_id,
        "task": task,
        "state": state,
    }


def _resolve_session(session_id: Optional[str]) -> tuple[str, EnvSession]:
    resolved = session_id or DEFAULT_SESSION_ID
    session = SESSIONS.get(resolved)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found. Call /reset first.")
    return resolved, session


def _coerce_action(request: StepRequest, env: WarehouseEnv) -> ActionModel:
    if request.order_quantities is not None:
        return ActionModel(order_quantities=request.order_quantities)

    payload = request.action
    if isinstance(payload, list):
        return ActionModel(order_quantities=payload)
    if isinstance(payload, dict):
        if "order_quantities" in payload:
            return ActionModel(order_quantities=list(payload["order_quantities"]))
        if "actions" in payload:
            return ActionModel(order_quantities=list(payload["actions"]))

    return ActionModel(order_quantities=[0] * env.config.num_skus)


async def _read_json(request: Request) -> Dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Warehouse Optimizer</title>
  <style>
    :root {
      --bg: #f3f6fb;
      --panel: #ffffff;
      --ink: #16202a;
      --muted: #5f6b76;
      --accent: #0b5ed7;
      --line: #d6dde8;
      --success: #1f7a4d;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background:
        radial-gradient(circle at top left, #dbeafe 0, transparent 28%),
        radial-gradient(circle at bottom right, #d1fae5 0, transparent 24%),
        var(--bg);
      color: var(--ink);
    }
    .wrap {
      max-width: 980px;
      margin: 0 auto;
      padding: 48px 20px 64px;
    }
    .hero, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 10px 30px rgba(12, 23, 36, 0.06);
    }
    .hero {
      padding: 36px;
      margin-bottom: 22px;
    }
    h1 {
      margin: 0 0 12px;
      font-size: 2.2rem;
      line-height: 1.1;
    }
    p {
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
      font-size: 1rem;
    }
    .status {
      display: inline-block;
      margin-bottom: 16px;
      padding: 8px 12px;
      border-radius: 999px;
      background: #e9f7ef;
      color: var(--success);
      font-weight: 600;
      font-size: 0.92rem;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 18px;
      margin-top: 22px;
    }
    .panel {
      padding: 22px;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 1.05rem;
    }
    ul {
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.7;
    }
    code {
      background: #eef3f8;
      padding: 2px 6px;
      border-radius: 6px;
      font-family: Consolas, monospace;
      color: var(--accent);
    }
    .footer {
      margin-top: 18px;
      color: var(--muted);
      font-size: 0.95rem;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="status">Environment server online</div>
      <h1>Warehouse Optimizer</h1>
      <p>
        This Space hosts the OpenEnv-compatible warehouse inventory optimization environment
        used for hackathon evaluation. The human-facing dashboard is not served here; this
        deployment is dedicated to the validator and API clients.
      </p>
    </section>
    <section class="grid">
      <div class="panel">
        <h2>Available Tasks</h2>
        <ul>
          <li><code>easy</code> single-SKU deterministic replenishment</li>
          <li><code>medium</code> multi-SKU stochastic replenishment</li>
          <li><code>hard</code> disruption-aware warehouse optimization</li>
        </ul>
      </div>
      <div class="panel">
        <h2>API Endpoints</h2>
        <ul>
          <li><code>GET /health</code></li>
          <li><code>POST /reset</code></li>
          <li><code>POST /step</code></li>
          <li><code>GET /state</code></li>
          <li><code>POST /state</code></li>
        </ul>
      </div>
      <div class="panel">
        <h2>Purpose</h2>
        <ul>
          <li>Hackathon validator target</li>
          <li>OpenEnv-compatible environment server</li>
          <li>Baseline client support via <code>inference.py</code></li>
        </ul>
      </div>
    </section>
    <div class="footer">
      API status remains available at <code>/health</code>. Environment interactions should use
      <code>/reset</code>, <code>/step</code>, and <code>/state</code>.
    </div>
  </div>
</body>
</html>
"""


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/reset")
async def reset(request: Request) -> Dict[str, Any]:
    body = await _read_json(request)
    payload = ResetRequest(
        task=body.get("task") or body.get("task_id") or body.get("difficulty") or "medium",
        seed=body.get("seed"),
    )
    task = payload.task.lower()
    env = _build_env(task)
    observation = env.reset(seed=payload.seed)
    session_id = str(uuid.uuid4())
    session = EnvSession(env=env, task=task)
    SESSIONS[session_id] = session
    SESSIONS[DEFAULT_SESSION_ID] = session

    return {
        "session_id": session_id,
        "task": task,
        "observation": _serialize_observation(observation),
        "reward": 0.0,
        "done": False,
        "info": {
            "message": "Environment reset successful.",
            "max_episode_steps": env.config.max_episode_steps,
            "num_skus": env.config.num_skus,
        },
    }


@app.post("/step")
async def step(request: Request) -> Dict[str, Any]:
    body = await _read_json(request)
    payload = StepRequest(
        session_id=body.get("session_id") or body.get("episode_id"),
        action=body.get("action") or body.get("actions"),
        order_quantities=body.get("order_quantities"),
    )
    session_id, session = _resolve_session(payload.session_id)
    action = _coerce_action(payload, session.env)
    result = session.env.step(action)

    return {
        "session_id": session_id,
        "task": session.task,
        "observation": _serialize_observation(result.observation),
        "reward": result.reward,
        "done": result.done,
        "info": result.info,
    }


@app.get("/state")
def state(session_id: Optional[str] = None) -> Dict[str, Any]:
    resolved_session_id, session = _resolve_session(session_id)
    return _serialize_state(session.env, resolved_session_id, session.task)


@app.post("/state")
async def state_post(request: Request) -> Dict[str, Any]:
    body = await _read_json(request)
    payload = StateRequest(session_id=body.get("session_id") or body.get("episode_id"))
    resolved_session_id, session = _resolve_session(payload.session_id)
    return _serialize_state(session.env, resolved_session_id, session.task)
