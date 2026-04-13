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
import google.auth.aio.transport.mtls as auth_mtls

# MUST BE SET BEFORE ANY IMPORTS THAT INITIALIZE CLIENTS
os.environ["GOOGLE_API_USE_MTLS"] = "never"

# Monkey patch to fix mTLS NoneType error on CloudTop
original_make_client_cert_ssl_context = auth_mtls.make_client_cert_ssl_context

def patched_make_client_cert_ssl_context(cert_bytes, key_bytes, passphrase=None):
    if cert_bytes is None:
        return ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    return original_make_client_cert_ssl_context(cert_bytes, key_bytes, passphrase)

auth_mtls.make_client_cert_ssl_context = patched_make_client_cert_ssl_context

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

import google.auth

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = "gab-ce-demos-1" 
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

from experience_analyst_agent.tools.read_interactions import read_interactions

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
