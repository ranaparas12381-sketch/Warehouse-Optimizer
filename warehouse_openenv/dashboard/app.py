"""Streamlit dashboard for warehouse optimization OpenEnv."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

import numpy as np
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baseline.run_baseline import run_simulation
from dashboard.components import (
    COLORS,
    build_demand_fulfillment_chart,
    build_inventory_chart,
    build_reward_chart,
    build_sku_table,
    inject_global_css,
    render_episode_log,
    render_kpi_card,
    style_sku_table,
)


DEFAULT_WEIGHTS: Dict[str, float] = {
    "w1": 0.4,
    "w2": 0.15,
    "w3": 0.25,
    "w4": 0.1,
    "w5": 0.05,
    "w6": 0.05,
}


def _collect_weight_inputs() -> Dict[str, float]:
    """Render reward weight controls and return selected weights."""
    with st.sidebar.expander("Advanced Configuration", expanded=False):
        st.caption("Reward Function Parameters")
        w1 = st.slider("Fulfillment Weight", 0.0, 1.0, DEFAULT_WEIGHTS["w1"], 0.01, help="Weight for fulfillment reward")
        w2 = st.slider("Holding Cost Weight", 0.0, 1.0, DEFAULT_WEIGHTS["w2"], 0.01, help="Weight for inventory holding costs")
        w3 = st.slider("Stockout Cost Weight", 0.0, 1.0, DEFAULT_WEIGHTS["w3"], 0.01, help="Weight for stockout penalties")
        w4 = st.slider("Order Cost Weight", 0.0, 1.0, DEFAULT_WEIGHTS["w4"], 0.01, help="Weight for ordering costs")
        w5 = st.slider("Capacity Violation Weight", 0.0, 1.0, DEFAULT_WEIGHTS["w5"], 0.01, help="Weight for capacity constraint violations")
        w6 = st.slider("Efficiency Bonus Weight", 0.0, 1.0, DEFAULT_WEIGHTS["w6"], 0.01, help="Weight for inventory efficiency bonus")

    return {"w1": w1, "w2": w2, "w3": w3, "w4": w4, "w5": w5, "w6": w6}


def _sidebar_controls() -> Dict[str, object]:
    """Render sidebar controls and return selected run configuration."""
    st.sidebar.markdown(
        f"""
<div style="padding: 1rem 0 1.5rem 0; border-bottom: 2px solid {COLORS['grid_lines']};">
  <div style="font-size:1.4rem; font-weight:700; color:{COLORS['accent_primary']};">
    Warehouse Operations
  </div>
  <div style="font-size:0.85rem; color:{COLORS['text_secondary']}; margin-top:0.5rem;">
    Inventory Optimization System
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    task_label = st.sidebar.radio("Task Difficulty", options=["Easy", "Medium", "Hard"], index=1)
    seed = st.sidebar.number_input("Random Seed", min_value=0, max_value=100000, value=42, step=1)
    episodes = st.sidebar.slider("Number of Episodes", min_value=1, max_value=50, value=10, step=1)

    reward_weights = _collect_weight_inputs()

    run_clicked = st.sidebar.button("RUN SIMULATION", use_container_width=True)
    return {
        "task": task_label.lower(),
        "seed": int(seed),
        "episodes": int(episodes),
        "reward_weights": reward_weights,
        "run": run_clicked,
    }


def _render_kpis(results: Dict[str, object]) -> None:
    trace = results.get("first_episode_trace", [])
    breakdown = results.get("breakdown_mean", {})

    avg_fulfillment = 100.0 * float(np.mean([row.get("fulfillment_rate", 0.0) for row in trace])) if trace else 0.0
    total_stockouts = int(sum(int(row.get("stockout_count", 0)) for row in trace)) if trace else 0

    if "cost_efficiency" in breakdown:
        cost_efficiency = 100.0 * float(breakdown.get("cost_efficiency", 0.0))
    else:
        total_cost = float(sum(row.get("total_cost", 0.0) for row in trace)) if trace else 0.0
        scale = max(total_cost, 1.0)
        cost_efficiency = 100.0 * max(0.0, min(1.0, 1.0 - (total_cost / (scale + total_cost))))

    col1, col2, col3, col4 = st.columns(4, gap="small")
    with col1:
        render_kpi_card("Final Score", f"{float(results.get('score_mean', 0.0)):.3f}", COLORS["accent_primary"])
    with col2:
        render_kpi_card("Avg Fulfillment Rate", f"{avg_fulfillment:.1f}%", COLORS["accent_success"])
    with col3:
        render_kpi_card("Total Stockouts", f"{total_stockouts}", COLORS["accent_danger"])
    with col4:
        render_kpi_card("Cost Efficiency", f"{cost_efficiency:.1f}%", COLORS["accent_warning"])


def _render_charts(results: Dict[str, object]) -> None:
    trace = results.get("first_episode_trace", [])
    sku_count = len(results.get("sku_config", []))

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        st.plotly_chart(build_inventory_chart(trace, sku_count), use_container_width=True)
    with c2:
        st.plotly_chart(build_demand_fulfillment_chart(trace), use_container_width=True)
    with c3:
        st.plotly_chart(build_reward_chart(trace), use_container_width=True)


def _render_details(results: Dict[str, object]) -> None:
    trace = results.get("first_episode_trace", [])
    sku_config = results.get("sku_config", [])

    left, right = st.columns([3, 2], gap="small")
    with left:
        st.subheader("Per-SKU Performance Table")
        table = build_sku_table(trace, sku_config)
        st.dataframe(style_sku_table(table), use_container_width=True, hide_index=True)

    with right:
        st.subheader("Episode Log")
        render_episode_log(trace)


def main() -> None:
    """Launch the warehouse operations dashboard."""
    st.set_page_config(
        page_title="Warehouse Inventory Management",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_global_css()

    controls = _sidebar_controls()

    if "results" not in st.session_state:
        st.session_state["results"] = None

    if controls["run"]:
        with st.spinner("Running simulation episodes..."):
            st.session_state["results"] = run_simulation(
                task=str(controls["task"]),
                seed=int(controls["seed"]),
                episodes=int(controls["episodes"]),
                reward_weights=dict(controls["reward_weights"]),
            )

    results = st.session_state.get("results")
    if not results:
        st.markdown(
            f"""
<div style="background:{COLORS['surface']}; border:2px solid {COLORS['grid_lines']};
            border-radius:8px; padding:2rem; color:{COLORS['text_secondary']}; margin-top:1rem;">
<div style="font-size:1.2rem; font-weight:600; color:{COLORS['text_primary']}; margin-bottom:1rem;">
Welcome to Warehouse Inventory Management System
</div>
<p style="line-height:1.6;">
Configure your simulation parameters using the sidebar controls and click <b style="color:{COLORS['accent_primary']};">RUN SIMULATION</b>
to begin the optimization process. The system will display key performance indicators, visualizations, and detailed analytics.
</p>
</div>
""",
            unsafe_allow_html=True,
        )
        return

    _render_kpis(results)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    _render_charts(results)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    _render_details(results)


if __name__ == "__main__":
    main()
