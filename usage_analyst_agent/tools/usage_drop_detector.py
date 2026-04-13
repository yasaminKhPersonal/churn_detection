import os
from google.cloud import bigquery

def usage_drop_detector(query: str = "") -> str:
    """Queries BigQuery to check for customers at risk of churn based on a 50% drop in 30-day moving average vs 90 days ago.

    Args:
        query: Optional query string, not used but needed for tool signature if called by agent with arguments.

    Returns:
        A string listing flagged customers or a summary.
    """
    print(f"DEBUG: usage_drop_detector called with query='{query}'")
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "gab-ce-demos-1")
    table_name = "gab-ce-demos-1.churn_detection.consumption_stats_yearly"

    client = bigquery.Client(project=project_id)

    # SQL query with Window Function
    sql = f"""
    WITH daily_sums_base AS (
        SELECT
            customer_id,
            usage_date,
            SUM(active_minutes) OVER(
                PARTITION BY customer_id 
                ORDER BY usage_date 
                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ) as sum_30d
        FROM `{table_name}`
    ),
    daily_sums_lagged AS (
        SELECT
            customer_id,
            usage_date,
            sum_30d,
            LAG(sum_30d, 30) OVER(
                PARTITION BY customer_id 
                ORDER BY usage_date
            ) as sum_30d_prev,
            ROW_NUMBER() OVER(PARTITION BY customer_id ORDER BY usage_date DESC) as rn
        FROM daily_sums_base
    )
    SELECT
        customer_id,
        (sum_30d_prev - sum_30d) as raw_drop,
        ((sum_30d_prev - sum_30d) / sum_30d_prev) * 100 as percentage_drop
    FROM daily_sums_lagged
    WHERE rn = 1 AND sum_30d < 0.8 * sum_30d_prev
    """

    try:
        query_job = client.query(sql)
        results = query_job.result()

        lines = []
        for row in results:
            lines.append(f"Customer {row.customer_id}: Raw Drop = {row.raw_drop:.2f}, Percentage Drop = {row.percentage_drop:.2f}%")

        print(f"DEBUG: usage_drop_detector found {len(lines)} flagged customers")
        if lines:
            return "\n".join(lines)
        else:
            return "No customers flagged as High Churn Risk based on usage drop."
    except Exception as e:
        return f"Error querying BigQuery: {str(e)}. Please ensure the table name is correct and accessible."
