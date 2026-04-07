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
from baseline.run_baseline import run_simulation  # noqa: E402
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


class SimulateRequest(BaseModel):
    task: str = Field(default="medium")
    seed: int = Field(default=42)
    episodes: int = Field(default=10)
    reward_weights: Optional[Dict[str, float]] = Field(default=None)


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
    html, body {
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: #f4f7fb;
      font-family: "Segoe UI", Arial, sans-serif;
    }
    .frame {
      width: 100%;
      height: 100vh;
      border: 0;
      display: block;
    }
    .fallback {
      display: none;
      height: 100vh;
      align-items: center;
      justify-content: center;
      padding: 24px;
      color: #1f2937;
      background:
        radial-gradient(circle at top left, #dbeafe 0, transparent 28%),
        radial-gradient(circle at bottom right, #d1fae5 0, transparent 24%),
        #f4f7fb;
    }
    .fallback-card {
      max-width: 680px;
      background: #fff;
      border: 1px solid #d6dde8;
      border-radius: 18px;
      box-shadow: 0 10px 30px rgba(12, 23, 36, 0.06);
      padding: 28px;
    }
    h1 {
      margin: 0 0 12px;
      font-size: 2rem;
    }
    p {
      margin: 0 0 12px;
      line-height: 1.6;
      color: #5f6b76;
    }
    a {
      color: #0b5ed7;
      text-decoration: none;
      font-weight: 600;
    }
    .badge {
      display: inline-block;
      padding: 8px 12px;
      border-radius: 999px;
      background: #e9f7ef;
      color: #1f7a4d;
      font-weight: 600;
      font-size: 0.92rem;
    }
  </style>
</head>
<body>
  <iframe
    id="renderApp"
    class="frame"
    src="https://warehouse-optimization-see0.onrender.com"
    title="Warehouse Optimizer"
    referrerpolicy="no-referrer"
  ></iframe>
  <div id="fallback" class="fallback">
    <div class="fallback-card">
      <div class="badge">Render dashboard unavailable in embedded view</div>
      <h1>Warehouse Optimizer</h1>
      <p>The live interactive dashboard is hosted on Render. If your browser blocks the embedded view, open it directly using the link below.</p>
      <p><a href="https://warehouse-optimization-see0.onrender.com" target="_blank" rel="noopener noreferrer">Open the live dashboard</a></p>
    </div>
  </div>
  <script>
    const frame = document.getElementById("renderApp");
    const fallback = document.getElementById("fallback");
    let loaded = false;
    frame.addEventListener("load", () => {
      loaded = true;
    });
    setTimeout(() => {
      if (!loaded) {
        fallback.style.display = "flex";
      }
    }, 5000);
  </script>
</body>
</html>
"""


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/simulate")
def simulate(request: Optional[SimulateRequest] = None) -> Dict[str, Any]:
    payload = request or SimulateRequest()
    task = payload.task.lower()
    if task not in TASK_FACTORIES:
        raise HTTPException(status_code=400, detail=f"Unsupported task '{task}'. Choose from easy, medium, hard.")
    return run_simulation(
        task=task,
        seed=int(payload.seed),
        episodes=int(payload.episodes),
        reward_weights=payload.reward_weights,
    )


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
