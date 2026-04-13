import os
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
import google.auth

from experience_analyst_agent.tools.read_interactions import read_interactions

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = "gab-ce-demos-1" 
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

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
