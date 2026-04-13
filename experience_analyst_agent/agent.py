import os
import json
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
import google.auth
from google.cloud import bigquery

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = os.environ.get("GOOGLE_CLOUD_PROJECT", "YOUR_PROJECT_ID")
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

def read_interactions(user_id: str = None) -> str:
    """Queries BigQuery to read interactions for a given user or all users if None.

    Args:
        user_id: Optional ID of the user to fetch interactions for.

    Returns:
        A JSON string containing the interactions or an error message.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "YOUR_PROJECT_ID")
    table_name = os.environ.get("INTERACTIONS_TABLE", "YOUR_PROJECT_ID.YOUR_DATASET.omnichannel_customer_interactions")

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

instruction = """You are a Customer Experience Analyst. Your role is to analyze customer interactions and assess their sentiment.

You have two modes of operation:
1. **Per-Customer Analysis**: If a user_id is provided, read the raw_interactions for that user and assign a sentiment_score from 1 to 10. Return a JSON object with sentiment_score and a brief reasoning string summarizing the trend.
2. **Batch Analysis**: If no user_id is provided, use the read_interactions tool without arguments to fetch interactions for ALL users. Analyze the interactions for each user, identify those with declining experience, and specifically flag users where the sentiment score is less than 5. Return a list of flagged users with their scores and reasoning.

Scoring Rubric:
1-2: Explicit churn threat, 'cancel', 'competitor', 'angry'.
3-4: Functional frustration, 'unusable', 'slow', 'confusing'.
5-6: Neutral, task-oriented questions.
7-10: Positive, 'thanks', 'love it', 'renew'.
"""

experience_analyst_agent = Agent(
    name="experience_analyst_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[read_interactions],
)

app = App(
    root_agent=experience_analyst_agent,
    name="experience_analyst_agent",
)
