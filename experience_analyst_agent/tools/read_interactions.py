import os
import json
from google.cloud import bigquery

def read_interactions(user_id: str = None) -> str:
    """Queries BigQuery to read interactions for a given user or all users if None.

    Args:
        user_id: Optional ID of the user to fetch interactions for.

    Returns:
        A JSON string containing the interactions or an error message.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "gab-ce-demos-1")
    table_name = "gab-ce-demos-1.churn_detection.omnichannel_customer_interactions"

    client = bigquery.Client(project=project_id)

    if user_id:
        sql = f"""
        SELECT `User ID` as user_id, `Date` as date, `Source` as source, `Raw Interaction Text` as text
        FROM `{table_name}`
        WHERE `User ID` = @user_id
        ORDER BY `Date` DESC
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
            ]
        )
    else:
        sql = f"""
        SELECT `User ID` as user_id, `Date` as date, `Source` as source, `Raw Interaction Text` as text
        FROM `{table_name}`
        ORDER BY `User ID`, `Date` DESC
        """
        job_config = None

    try:
        if job_config:
            query_job = client.query(sql, job_config=job_config)
        else:
            query_job = client.query(sql)
        results = query_job.result()

        interactions = []
        for row in results:
            interactions.append({
                "user_id": row.user_id,
                "date": str(row.date),
                "source": row.source,
                "text": row.text
            })

        return json.dumps(interactions, indent=2)
    except Exception as e:
        return f"Error querying BigQuery: {str(e)}"
