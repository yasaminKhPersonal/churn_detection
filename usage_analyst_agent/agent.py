# ruff: noqa
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

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

import google.auth

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = "gab-ce-demos-1" 
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
from usage_analyst_agent.tools.usage_drop_detector import usage_drop_detector

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
