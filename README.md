# Churn Detection Multi-Agent System

Multi-agent system for customer churn detection using Google Cloud Vertex AI and BigQuery.

## Agents

- **`churn_root_agent`**: Orchestrates the workflow by calling specialized agents, combining their signals, and ranking at-risk customers by the magnitude of their raw usage drop.
- **`usage_analyst_agent`**: Queries BigQuery to detect customers with significant drops in usage by comparing recent moving averages to historical data.
- **`experience_analyst_agent`**: Analyzes customer interaction logs and uses Gemini to assess sentiment and identify frustrated customers.
