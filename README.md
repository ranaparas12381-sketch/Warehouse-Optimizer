WAREHOUSE INVENTORY OPTIMIZATION SYSTEM

A sophisticated reinforcement learning environment for warehouse inventory management and optimization.

DESCRIPTION

This project implements an advanced simulation environment for warehouse inventory optimization using state of the art reinforcement learning techniques and operations research methodologies. The system provides realistic modeling of multi SKU logistics operations including demand forecasting, capacity management, and cost optimization.

KEY FEATURES

* Multi SKU inventory management with configurable complexity levels
* Realistic demand modeling with seasonality and trend analysis
* Stochastic supplier lead time simulation
* Comprehensive cost optimization including holding costs, stockout penalties, and ordering expenses
* Interactive web dashboard for real time visualization and analysis
* Configurable reward functions with multiple optimization objectives
* Three difficulty levels for progressive learning and evaluation

TECHNICAL STACK

* Python 3.11
* Streamlit for interactive web interface
* Plotly for advanced data visualization
* Pydantic for robust data validation
* NumPy and Pandas for numerical computation
* Docker for containerized deployment

QUICK START

Prerequisites

* Python 3.11 or higher
* pip package manager
* Docker (optional for containerized deployment)

Installation

Clone the repository and install dependencies:

git clone <repository-url>
cd warehouse-optimization/warehouse_openenv
pip install -r requirements.txt

Running the Application

Launch the interactive dashboard:

streamlit run dashboard/app.py

The application will be available at http://localhost:8501

Running Baseline Simulations

Execute baseline policy simulations from the command line:

python -m baseline.run_baseline --task medium --seed 42 --episodes 10

Available tasks: easy, medium, hard

DOCKER DEPLOYMENT

Local Docker Deployment

Build and run the Docker container:

docker build -t warehouse-optimization ./warehouse_openenv
docker run -p 8501:8501 warehouse-optimization

Using Docker Compose

docker-compose up

DEPLOYMENT ON RENDER

This application is configured for deployment on Render using the included render.yaml configuration file.

Steps for Render Deployment:

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Render will automatically detect the render.yaml configuration in the repository root
4. Click Create Web Service
5. The application will be built and deployed automatically

The Render blueprint is configured to build from `warehouse_openenv/Dockerfile` with `warehouse_openenv` as the Docker context, so the Render service root directory should be left empty.

The render.yaml file contains all necessary configuration including environment variables and health check endpoints.

SYSTEM ARCHITECTURE

The project follows a modular architecture:

* env: Core simulation engine and environment logic
* tasks: Task definitions and difficulty configurations
* graders: Performance evaluation and scoring systems
* baseline: Reference implementations and heuristic policies
* dashboard: Web interface and visualization components

TASK DIFFICULTY LEVELS

Easy: Single SKU with deterministic demand patterns
Medium: Multiple SKUs with stochastic demand and variable lead times
Hard: Full warehouse simulation with capacity constraints and demand disruptions

PERFORMANCE METRICS

The system evaluates performance across multiple dimensions:

* Fulfillment rate: Percentage of demand successfully met
* Cost efficiency: Optimization of holding and ordering costs
* Stockout frequency: Minimization of inventory shortages
* Service level: Overall reliability and customer satisfaction

CONFIGURATION

The system supports extensive configuration through:

* Reward weight parameters for multi objective optimization
* Task specific difficulty parameters
* Random seed control for reproducible experiments
* Episode length and simulation parameters

CONTRIBUTING

Contributions are welcome. Please ensure code follows the existing architecture patterns and includes appropriate tests.
