"""Baseline heuristics and evaluation script for warehouse OpenEnv tasks."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Tuple

import click

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from env.models import ActionModel, StepResult, WarehouseConfig
from env.utils import moving_average
from env.warehouse_env import WarehouseEnv
from graders import GRADER_REGISTRY
from tasks.easy import make_config as make_easy_config
from tasks.hard import make_config as make_hard_config
from tasks.medium import make_config as make_medium_config


TASK_CONFIG_FACTORY = {
    "easy": make_easy_config,
    "medium": make_medium_config,
    "hard": make_hard_config,
}


def _build_env(task: str, reward_weights: Optional[Dict[str, float]] = None) -> WarehouseEnv:
    config = TASK_CONFIG_FACTORY[task]()
    if reward_weights:
        config.reward_weights = {**config.reward_weights, **reward_weights}
    return WarehouseEnv(config)


def _easy_policy(env: WarehouseEnv) -> ActionModel:
    state = env.state()
    orders: List[int] = []
    for sku_idx, sku in enumerate(state.config.skus):
        current_stock = state.current_inventory[sku_idx]
        if current_stock < sku.reorder_point:
            orders.append(max(0, sku.max_stock - current_stock))
        else:
            orders.append(0)
    return ActionModel(order_quantities=orders)


def _medium_policy(env: WarehouseEnv) -> ActionModel:
    state = env.state()
    orders: List[int] = []

    for sku_idx, sku in enumerate(state.config.skus):
        on_hand = state.current_inventory[sku_idx]
        on_order = sum(
            qty for arrival_t, qty in enumerate(state.pipeline_orders[sku_idx]) if arrival_t >= state.time_step
        )

        lead = max(1.0, sku.supplier_lead_time_mean)
        safety_stock = 1.65 * sku.demand_std * (lead ** 0.5)
        reorder_level = int(round((sku.demand_mean * lead) + safety_stock))

        inventory_position = on_hand + on_order
        if inventory_position < reorder_level:
            q = int(round(sku.max_stock - inventory_position))
            orders.append(max(0, q))
        else:
            orders.append(0)

    return ActionModel(order_quantities=orders)


def _hard_policy(env: WarehouseEnv) -> ActionModel:
    state = env.state()
    orders: List[int] = []

    for sku_idx, sku in enumerate(state.config.skus):
        demand_history = state.demand_history[sku_idx]
        demand_estimate = moving_average(demand_history, window=7)
        if demand_estimate <= 0:
            demand_estimate = sku.demand_mean

        seasonality_buffer = 1.0 + sku.seasonality_amplitude * 0.6
        expected_lead_demand = demand_estimate * max(1.0, sku.supplier_lead_time_mean) * seasonality_buffer
        safety_stock = 2.05 * sku.demand_std * (max(1.0, sku.supplier_lead_time_mean) ** 0.5)
        target_stock = min(sku.max_stock, int(round(expected_lead_demand + safety_stock)))

        on_hand = state.current_inventory[sku_idx]
        on_order = sum(
            qty for arrival_t, qty in enumerate(state.pipeline_orders[sku_idx]) if arrival_t >= state.time_step
        )
        inventory_position = on_hand + on_order

        order_qty = max(0, target_stock - inventory_position)
        orders.append(order_qty)

    # Tight capacity control for hard scenario.
    projected_inventory = sum(state.current_inventory) + sum(orders)
    overflow = max(0, projected_inventory - state.config.warehouse_capacity)
    if overflow > 0 and sum(orders) > 0:
        shrink_ratio = max(0.0, 1.0 - (overflow / sum(orders)))
        orders = [int(round(q * shrink_ratio)) for q in orders]

    return ActionModel(order_quantities=orders)


def _policy_for_task(task: str, env: WarehouseEnv) -> ActionModel:
    if task == "easy":
        return _easy_policy(env)
    if task == "medium":
        return _medium_policy(env)
    return _hard_policy(env)


def _run_episode(env: WarehouseEnv, task: str, seed: int) -> Tuple[List[StepResult], List[Dict[str, Any]]]:
    env.reset(seed=seed)
    done = False
    results: List[StepResult] = []
    logs: List[Dict[str, Any]] = []

    while not done:
        action = _policy_for_task(task, env)
        step_result = env.step(action)
        results.append(step_result)
        logs.append(
            {
                "step": int(step_result.info.get("time_step", len(results))),
                "reward": float(step_result.reward),
                "stock": list(step_result.info.get("inventory", [])),
                "demand": list(step_result.info.get("demand", [])),
                "fulfilled": list(step_result.info.get("fulfilled", [])),
                "stockout_count": int(step_result.info.get("stockout_count", 0)),
                "total_cost": float(step_result.info.get("total_cost", 0.0)),
                "fulfillment_rate": float(step_result.info.get("fulfillment_rate", 0.0)),
                "disrupted": bool(step_result.info.get("disrupted", False)),
            }
        )
        done = step_result.done

    return results, logs


def run_simulation(
    task: str = "medium",
    seed: int = 42,
    episodes: int = 10,
    reward_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Run baseline policy for a task and return detailed metrics."""
    if task not in TASK_CONFIG_FACTORY:
        raise ValueError(f"Unsupported task '{task}'. Choose from {list(TASK_CONFIG_FACTORY.keys())}")

    env = _build_env(task, reward_weights=reward_weights)
    grader = GRADER_REGISTRY[task]()

    episode_scores: List[float] = []
    episode_breakdowns: List[Dict[str, float]] = []
    traces: List[List[Dict[str, Any]]] = []

    for episode in range(episodes):
        episode_seed = seed + episode
        results, logs = _run_episode(env, task, episode_seed)
        score = grader.grade(results)
        details = grader.breakdown(results)

        episode_scores.append(float(score))
        episode_breakdowns.append(details)
        traces.append(logs)

    score_mean = float(mean(episode_scores)) if episode_scores else 0.0
    score_std = float(pstdev(episode_scores)) if len(episode_scores) > 1 else 0.0

    aggregate_breakdown: Dict[str, float] = {}
    if episode_breakdowns:
        for key in episode_breakdowns[0].keys():
            aggregate_breakdown[key] = float(mean(b[key] for b in episode_breakdowns))

    first_trace = traces[0] if traces else []

    return {
        "task": task,
        "seed": seed,
        "episodes": episodes,
        "scores": episode_scores,
        "score_mean": score_mean,
        "score_std": score_std,
        "breakdown_mean": aggregate_breakdown,
        "episode_breakdowns": episode_breakdowns,
        "first_episode_trace": first_trace,
        "sku_config": [sku.model_dump() for sku in env.config.skus],
    }


def _save_results(payload: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@click.command()
@click.option("--task", default="medium", type=click.Choice(["easy", "medium", "hard"], case_sensitive=False))
@click.option("--seed", default=42, type=int)
@click.option("--episodes", default=10, type=click.IntRange(1, 500))
def main(task: str, seed: int, episodes: int) -> None:
    """CLI entry point for baseline evaluation."""
    normalized_task = task.lower()
    payload = run_simulation(task=normalized_task, seed=seed, episodes=episodes)

    print(f"Task: {normalized_task}")
    print(f"Episodes: {episodes}")
    print(f"Seed: {seed}")
    print("Per-episode scores:")
    for idx, score in enumerate(payload["scores"], start=1):
        print(f"  Episode {idx:02d}: {score:.4f}")

    print(f"Score mean +- std: {payload['score_mean']:.4f} +- {payload['score_std']:.4f}")
    print("Mean metric breakdown:")
    for key, value in payload["breakdown_mean"].items():
        print(f"  {key}: {value:.4f}")

    output_file = Path("results") / f"baseline_{normalized_task}_{seed}.json"
    _save_results(payload, output_file)
    print(f"Saved results to: {output_file}")


if __name__ == "__main__":
    main()
