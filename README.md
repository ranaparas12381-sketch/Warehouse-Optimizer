---
title: Warehouse Optimizer
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# Warehouse Optimizer

Warehouse Optimizer is an OpenEnv-compatible warehouse inventory environment for evaluating replenishment policies under deterministic, stochastic, and disruption-aware operating conditions.

The project exposes a simple HTTP environment server for hackathon validation and agent integration, while also keeping the underlying simulation modules and dashboard code available in the repository.

## Overview

The environment models multi-SKU warehouse operations with:

- inventory position tracking
- stochastic demand generation
- supplier lead times
- holding, ordering, and stockout costs
- capacity constraints
- task-based difficulty levels

Available tasks:

- `easy`: single-SKU deterministic replenishment
- `medium`: multi-SKU stochastic replenishment
- `hard`: disruption-aware warehouse optimization

## Repository Structure

- `app.py`: FastAPI server exposing `/reset`, `/step`, `/state`, and `/health`
- `inference.py`: baseline policy client for interacting with the HTTP environment
- `openenv.yaml`: OpenEnv submission metadata
- `requirements.txt`: root runtime dependencies for Docker and Hugging Face Spaces
- `warehouse_openenv/env`: simulation engine and state models
- `warehouse_openenv/tasks`: task-specific environment configurations
- `warehouse_openenv/graders`: evaluation logic
- `warehouse_openenv/baseline`: local baseline simulation utilities
- `warehouse_openenv/dashboard`: Streamlit dashboard code retained for local exploration

## API Endpoints

The root service exposes the following endpoints:

- `GET /health`
- `POST /reset`
- `POST /step`
- `GET /state`
- `POST /state`

Example reset request:

```json
{
  "task": "medium",
  "seed": 42
}
```

Example step request:

```json
{
  "session_id": "<session-id>",
  "order_quantities": [10, 0, 5, 0, 2]
}
```

## Local Development

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the OpenEnv server locally:

```bash
uvicorn app:app --host 0.0.0.0 --port 7860
```

Run the baseline client against the local server:

```bash
python inference.py --base-url http://127.0.0.1:7860 --task medium --seed 42
```

## Docker

Build the container:

```bash
docker build -t warehouse-optimizer .
```

Run the container:

```bash
docker run -p 7860:7860 warehouse-optimizer
```

## Deployment

### Hugging Face Spaces

The repository is configured as a Docker Space and serves the OpenEnv HTTP API on port `7860`.

### Render

The repository also includes a Render blueprint in [render.yaml](D:/Download/WarehouseOptimization/render.yaml). Render should build from `warehouse_openenv/Dockerfile` with the service root directory left empty.

## Notes

- The OpenEnv submission flow uses the root `Dockerfile`, root `openenv.yaml`, and root `inference.py`.
- The Streamlit dashboard is preserved in the repository for local visualization, but the production hackathon deployment runs the HTTP environment server.

## License

This project is released under the MIT License.
