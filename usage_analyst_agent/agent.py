import os
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
import google.auth

from usage_analyst_agent.tools.usage_drop_detector import usage_drop_detector

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = "gab-ce-demos-1" 
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

usage_analyst_agent = Agent(
    name="usage_analyst_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="You are a Usage Analyst Agent. Your job is to check BigQuery for customers at risk of churn and report them. Use the usage_drop_detector tool. You MUST include the raw drop value and percentage drop value for each customer in your response.",
    tools=[usage_drop_detector],
)

app = App(
    root_agent=usage_analyst_agent,
    name="usage_analyst_agent",
)
