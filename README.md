# Churn Detection Multi-Agent System

Multi-agent system for customer churn detection using Google Cloud Vertex AI and BigQuery.

## Agents

- **`churn_root_agent`**: Orchestrates the workflow and ranks customers.
- **`usage_analyst_agent`**: Detects usage drops via BigQuery.
- **`experience_analyst_agent`**: Analyzes customer interaction sentiment.
