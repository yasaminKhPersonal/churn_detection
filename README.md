# Churn Detection Multi-Agent System

This project implements a multi-agent system for customer churn detection using Google Cloud Vertex AI and BigQuery.

## Multi-Agent Architecture

This system uses a hierarchical multi-agent architecture to combine distinct analytical signals:

- **`churn_root_agent/`**: The orchestrator agent. It directs the workflow by first invoking the specialized agents, gathering their findings, combining the signals into a unified record for each customer, and finally ranking the at-risk customers based on the magnitude of their raw usage drop.
- **`usage_analyst_agent/`**: A specialized agent focused on quantitative analysis. It queries BigQuery to detect customers with significant drops in usage (based on window functions comparing recent moving averages to historical data).
- **`experience_analyst_agent/`**: A specialized agent focused on qualitative analysis. It reads customer interaction logs and uses Gemini to assess sentiment and identify frustrated customers.

## Project Structure

- **`churn_root_agent/`**: Contains the root agent definition.
- **`usage_analyst_agent/`**: Contains the usage analyst agent definition.
- **`experience_analyst_agent/`**: Contains the experience analyst agent definition.
