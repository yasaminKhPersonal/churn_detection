# Churn Detection Multi-Agent System

This project implements a multi-agent system for customer churn detection using Google Cloud Vertex AI and BigQuery.

## Project Structure

- **`churn_root_agent/`**: The root agent that orchestrates the workflow, combining signals from other agents.
- **`usage_analyst_agent/`**: Analyzes customer usage data in BigQuery to detect significant drops.
- **`experience_analyst_agent/`**: Analyzes customer interaction logs to assess sentiment.

## Quick Start

To start the local development playground:

```bash
uv run adk web . --port 8501 --reload_agents
```

Once started, open your browser and navigate to `http://localhost:8501/dev-ui/` to interact with the agents.
