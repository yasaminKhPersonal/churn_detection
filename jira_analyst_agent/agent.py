import os
import ssl
import sys
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

from google.adk.runners import InMemoryRunner
from google.adk.tools import McpToolset
from datetime import datetime
from google.adk.tools.mcp_tool.mcp_toolset import StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from dotenv import load_dotenv
import os

# Load environment variables early
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(os.path.dirname(current_dir), '.env')
load_dotenv(dotenv_path)
from google.genai import Client

# Monkey patch Gemini.api_client to force Vertex AI
def patched_api_client(self):
    import os
    return Client(
        vertexai=True,
        project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        http_options=types.HttpOptions(
            headers=self._tracking_headers(),
            retry_options=self.retry_options,
            base_url=self.base_url,
        )
    )

Gemini.api_client = property(patched_api_client)

# Monkey patch MCP Session to increase timeout from 5s to 60s.
# Jira API calls can be slow and cause timeout errors in the default MCP client.
from mcp.shared.session import BaseSession
from datetime import timedelta

original_send_request = BaseSession.send_request

async def patched_send_request(self, request, result_type, request_read_timeout_seconds=None, metadata=None, progress_callback=None):
    if request_read_timeout_seconds is None:
        request_read_timeout_seconds = timedelta(seconds=60)
    return await original_send_request(self, request, result_type, request_read_timeout_seconds, metadata, progress_callback)

BaseSession.send_request = patched_send_request


# 1. The Corrected Connection for Cloudtop
# We use the specific -c command to trigger the Atlassian server
jira_connection = StdioConnectionParams(
    server_params=StdioServerParameters(
        command=sys.executable, # Use venv python to ensure mcp-atlassian is found
        args=[
            "-c", 
            "from mcp_atlassian.servers.main import main_mcp; main_mcp.run()"
        ],
        env={
            "JIRA_URL": "https://khorramzy.atlassian.net",
            "JIRA_API_TOKEN": os.environ.get("JIRA_API_TOKEN"),
            "JIRA_USERNAME": os.environ.get("JIRA_USER_EMAIL"),
            "TOOLSETS": "all"
        }
    )
)

# 2. Initialize the Toolset
jira_tools = McpToolset(connection_params=jira_connection)

def get_today_date() -> str:
    """Returns today's date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")

# 3. Create the Agent
my_jira_agent = Agent(
    name="jira_analyst",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are a churn risk analyst. 
    Use your tools to search Jira for issues, analyze descriptions and comments for customer frustration (sentiment analysis).
    
    When you receive a prompt containing a Customer ID (e.g., 'CUST_XXXX'), you MUST:
    1. Search for issues in project 'CHUR' related to that customer (e.g., by searching for the Customer ID in labels or text).
    2. Assess Stagnation and Velocity risks for those specific issues.
    3. Return the report in the required table format.
    
    If no specific Customer ID is provided, search for all issues in project 'CHUR'.
    
    Pay special attention to:
    - **Labels**: When calling `jira_search` or `jira_get_issue`, you MUST explicitly request the `labels` field to find the Customer ID.
    - **Stagnation**: Tickets that have been open for a long time without updates. You MUST calculate the **number of days** the ticket has been stagnant. Use the `get_today_date` tool to find the current date for calculations.
    - **Velocity**: The rate of created tickets for each customer. You MUST calculate the **number of tickets per week or month** for that customer. If you cannot calculate a rate (e.g., only 1 ticket found), simply state the ticket count (e.g., '1 ticket').
    - **Customer ID**: Extract the Customer ID from the ticket labels (e.g., 'CUST_XXXX').
    
    OUTPUT FORMAT:
    You MUST return a valid JSON object mapping Customer IDs to their metrics. Do NOT add any intro or outro text, and do NOT wrap the JSON in markdown code blocks. Just return the raw JSON string.
    
    Example:
    {
      "CUST_1234": {"velocity": "5 tickets/month", "stagnation": "14 days", "frustration": "High"}
    }
    
    If a ticket does not have a Customer ID in labels, use "Unknown" as the key.
    You MUST calculate the values for velocity and stagnation and include the unit of measure (e.g., "days" for stagnation, "tickets/month" or "tickets/week" for velocity). Do NOT use qualitative words like "Good", "Slow", "High", "Low" for these fields.
    Use these concepts to identify churn risks for customers in project 'CHUR'.""",
    tools=[jira_tools, get_today_date]
)

app = App(
    root_agent=my_jira_agent,
    name="jira_analyst_agent",
)
