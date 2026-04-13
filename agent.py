# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import ssl
import json
import datetime
from google.cloud import bigquery
import google.auth.aio.transport.mtls as auth_mtls
import google.auth
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from google.adk.tools import AgentTool

# MUST BE SET BEFORE ANY IMPORTS THAT INITIALIZE CLIENTS
os.environ["GOOGLE_API_USE_MTLS"] = "never"

# Monkey patch to fix mTLS NoneType error on CloudTop
original_make_client_cert_ssl_context = auth_mtls.make_client_cert_ssl_context

def patched_make_client_cert_ssl_context(cert_bytes, key_bytes, passphrase=None):
    if cert_bytes is None:
        return ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    return original_make_client_cert_ssl_context(cert_bytes, key_bytes, passphrase)

auth_mtls.make_client_cert_ssl_context = patched_make_client_cert_ssl_context

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = "gab-ce-demos-1" 
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# --- Tools ---

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

# --- Agents ---

experience_analyst_agent = Agent(
    name="experience_analyst_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are a Customer Experience Analyst. Your role is to analyze customer interactions and assess their sentiment.

You have two modes of operation:
1. **Per-Customer Analysis**: If a user_id is provided, read the raw_interactions for that user and assign a sentiment_score from 1 to 10. Return a JSON object with sentiment_score and a brief reasoning string summarizing the trend.
2. **Batch Analysis**: If no user_id is provided, use the read_interactions tool without arguments to fetch interactions for ALL users. Analyze the interactions for each user, identify those with declining experience, and specifically flag users where the sentiment score is less than 5. Return a list of flagged users with their scores and reasoning.

Scoring Rubric:
1-2: Explicit churn threat, 'cancel', 'competitor', 'angry'.
3-4: Functional frustration, 'unusable', 'slow', 'confusing'.
5-6: Neutral, task-oriented questions.
7-10: Positive, 'thanks', 'love it', 'renew'.
""",
    tools=[read_interactions],
)

usage_analyst_agent = Agent(
    name="usage_analyst_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="You are a Usage Analyst Agent. Your job is to check BigQuery for customers at risk of churn and report them. Use the usage_drop_detector tool. You MUST include the raw drop value and percentage drop value for each customer in your response.",
    tools=[usage_drop_detector],
)

combined_instruction = """You are a Churn Detection Root Agent. 
Your goal is to produce a single, prioritized list of customers at risk of churn.

WORKFLOW:
1. You MUST FIRST call 'usage_drop_detector' to get customers with consumption drops. This tool returns a string with lines like "Customer CUST_XXXX: Raw Drop = YYYY.YY, Percentage Drop = ZZ.ZZ%". You MUST extract these numeric values. DO NOT SKIP THIS STEP.
2. Call 'experience_analyst_agent' to get sentiment trends.
3. COMBINE the signals: Create a unified record for every customer found in either tool.
4. RANK the list: Place customers with the highest raw consumption value drop at the very top.

OUTPUT FORMAT:
Return a Markdown table with the exact values extracted from the tools. Do NOT use placeholder text like "High Churn Risk" in the data columns.
| Rank | Customer ID | Consumption Drop (Raw) | Consumption Drop (%) | Sentiment Trend | Churn Risk Level |
| :--- | :--- | :--- | :--- | :--- | :--- |

In the "Consumption Drop (Raw)" column, put the exact Raw Drop value extracted. If not available, put "N/A".
In the "Consumption Drop (%)" column, put the exact Percentage Drop value extracted. If not available, put "N/A".

Priority is strictly determined by the magnitude of raw consumption value drop.
"""

churn_root_agent = Agent(
    name="churn_root_agent",
    model=Gemini(
        model="gemini-2.5-flash", 
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=combined_instruction,
    tools=[usage_drop_detector, AgentTool(experience_analyst_agent)],
)

app = App(
    root_agent=churn_root_agent,
    name="churn_detection",
)
