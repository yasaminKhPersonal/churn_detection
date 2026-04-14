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
os.environ["GOOGLE_CLOUD_PROJECT"] = os.environ.get("GOOGLE_CLOUD_PROJECT", "YOUR_PROJECT_ID")
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

from usage_analyst_agent.agent import usage_drop_detector
from experience_analyst_agent.agent import experience_analyst_agent
from jira_analyst_agent.agent import my_jira_agent

# Updated Instruction to use Usage Drop instead of Consumption Drop
combined_instruction = """You are a Churn Detection Root Agent. 

WORKFLOW:
1. **DETERMINE N**: Extract the number of customers requested from the user's prompt (e.g., "top 5"). Default to 3 if not specified.
2. **DATA COLLECTION**: Call 'usage_drop_detector', 'experience_analyst_agent', and 'jira_analyst' (Project 'CHUR').
3. **STRICT NUMERIC RULES (USAGE)**: 
   - Columns: 'Usage Change (Raw)' and 'Usage Change (%)'.
   - **DECREASE/DROP**: You MUST prefix with a MINUS SIGN (e.g., -500.00 or -12.5%).
   - **INCREASE/GROWTH**: Show as a POSITIVE number (e.g., 250.00 or 5.2%).
   - **NO DATA/STABLE**: Show as 0.00.
4. **TICKET VELOCITY (30-DAY COUNT)**:
   - Count the total number of Jira tickets created or resolved for the customer within the last 30 days (since March 14, 2026).
   - Format MUST be: "[Total Tickets] / 30 days".
   - ABSOLUTELY NO NULLS. If no tickets exist in this window, you MUST return "0 / 30 days".
5. **STAGNATION CALCULATION**:
   Get the 'created_at' date for the oldest open ticket from the Jira tool.
   - Calculate the difference in days between that date and TODAY's DATE (April 13, 2026).
   - Report only the whole number of days. If data is missing, state 'No open tickets'.
   
RANKING & MANDATORY FILL:
- Rank primarily by negative Usage Change (most severe loss first).
- **STRICT N-ROW REQUIREMENT**: You MUST return exactly N rows in the table. 
- **BACKFILL LOGIC**: If there are fewer than N customers with usage drops, fill the remaining rows with customers who have the highest 'Jira Stagnation' or 'Negative Sentiment', even if their usage change is 0.00 or positive. Do not stop until you reach N rows.

OUTPUT FORMAT:
- Return exactly N rows in this Markdown table.
| Rank | Customer ID | Usage Change (Raw) | Usage Change (%) | Sentiment | Jira Velocity (Tickets/Days) | Jira Stagnation (Days) | Churn Risk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |

EXPLANATION:
- For each row, justify the risk. If a row was included via Backfill Logic (e.g., positive usage but high stagnation), explicitly note: "Included due to high support friction despite growth."
"""

churn_root_agent = Agent(
    name="churn_root_agent",
    model=Gemini(
        model="gemini-2.5-flash", 
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=combined_instruction,
    tools=[usage_drop_detector, AgentTool(experience_analyst_agent), AgentTool(my_jira_agent)],
)

app = App(
    root_agent=churn_root_agent,
    name="churn_root_agent",
)
