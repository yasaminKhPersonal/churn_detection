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
from google.adk.tools import AgentTool

import google.auth

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = "gab-ce-demos-1" 
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

from usage_analyst_agent.tools.usage_drop_detector import usage_drop_detector
from experience_analyst_agent.agent import experience_analyst_agent

# Updated Instruction to enforce a combined data structure and ranking
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
    name="churn_root_agent",
)
