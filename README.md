# Churn Detection Multi-Agent System

Multi-agent system for customer churn detection using Google Cloud Vertex AI and BigQuery.

## Agents

- **`churn_root_agent`**: Orchestrates the workflow by calling specialized agents, combining their signals, and ranking at-risk customers by the magnitude of their raw usage drop.
- **`usage_analyst_agent`**: Queries BigQuery to detect customers with significant drops in usage by comparing recent moving averages to historical data.
- **`experience_analyst_agent`**: Analyzes customer interaction logs and uses Gemini to assess sentiment and identify frustrated customers.

## Configuration

To run this project, copy the `.env.example` file to `.env` and specify your Google Cloud Project and BigQuery table names:

```env
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
CONSUMPTION_TABLE=YOUR_PROJECT_ID.YOUR_DATASET.consumption_stats_yearly
INTERACTIONS_TABLE=YOUR_PROJECT_ID.YOUR_DATASET.omnichannel_customer_interactions
```

## Data Schema

Here are the expected schemas for the BigQuery tables used by the agents:

### Consumption Stats Table (`CONSUMPTION_TABLE`)
| Field Name | Type | Mode |
| :--- | :--- | :--- |
| **customer_id** | STRING | NULLABLE |
| **usage_date** | DATE | NULLABLE |
| **active_minutes** | INTEGER | NULLABLE |
| **feature_usage_count** | INTEGER | NULLABLE |
| **gb_processed** | FLOAT | NULLABLE |

### Omnichannel Customer Interactions Table (`INTERACTIONS_TABLE`)
| Field Name | Type | Mode |
| :--- | :--- | :--- |
| **User ID** | STRING | NULLABLE |
| **Date** | DATE | NULLABLE |
| **Source** | STRING | NULLABLE |
| **Raw Interaction Text** | STRING | NULLABLE |
