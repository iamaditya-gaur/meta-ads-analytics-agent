"""
Data Analyst Agent — fetches and parses Meta Ads data via the Graph API.

Architectural rules enforced:
  • temperature=0.0  (strict determinism)
  • All JSON parsing uses .get() with fallbacks — never direct key access
  • Credentials come from environment variables (never hardcoded)
  • 401 / OAuthException → immediate halt with actionable error message
  • 429 / 5xx → clean exit with actionable message (not a raw stack trace)
"""

import os
import requests
from crewai import Agent, LLM


TOKEN_EXPIRED_MESSAGE = (
    "CRITICAL ERROR: Meta API Token has expired. "
    "Please generate a new 60-day token and update the .env file. "
    "More info here: https://gemini.google.com/share/893368719666."
)


class MetaTokenExpiredError(Exception):
    """Raised when the Meta API returns 401 or an OAuthException."""

    def __init__(self):
        super().__init__(TOKEN_EXPIRED_MESSAGE)


class MetaAPIError(Exception):
    """Raised for non-auth Meta API failures (429, 500, etc.)."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        message = (
            f"Meta API request failed (HTTP {status_code}): {detail}\n"
            "If this is a rate-limit (429), wait a few minutes and retry. "
            "If it persists, check https://developers.facebook.com/status/ "
            "for platform outages."
        )
        super().__init__(message)


class DataAnalystAgent:
    """Encapsulates the Data Analyst agent and its Meta API data-fetching tool."""

    def __init__(self):
        self.access_token = os.environ["META_ACCESS_TOKEN"]
        self.ad_account_id = os.environ["META_AD_ACCOUNT_ID"]
        self.base_url = "https://graph.facebook.com/v22.0"

    # ------------------------------------------------------------------
    # Meta Graph API helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_token_error(response: requests.Response) -> None:
        """
        Inspect the API response for auth failures.

        Checks two conditions:
          1. HTTP 401 Unauthorized status code
          2. OAuthException in the JSON error body (Meta returns 400 for
             some token errors, so we can't rely on status alone)

        Raises MetaTokenExpiredError immediately on match.
        """
        if response.status_code == 401:
            raise MetaTokenExpiredError()

        try:
            body = response.json()
        except ValueError:
            return  # non-JSON response — let downstream handling deal with it

        error_obj = body.get("error", {})
        if error_obj.get("type", "N/A") == "OAuthException":
            raise MetaTokenExpiredError()

    def _make_request(self, url: str, params: dict) -> dict:
        """
        Execute a GET request against the Meta Graph API with full
        error handling.

        Returns the parsed JSON payload on success.

        Raises:
            MetaTokenExpiredError: on 401 / OAuthException
            MetaAPIError: on any other HTTP error (429, 5xx, etc.)
        """
        response = requests.get(url, params=params, timeout=30)
        self._check_token_error(response)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            # Extract detail from Meta's JSON error body if available
            try:
                error_body = response.json()
                detail = error_body.get("error", {}).get(
                    "message", response.text[:200]
                )
            except ValueError:
                detail = response.text[:200]
            raise MetaAPIError(response.status_code, detail)

        return response.json()

    @staticmethod
    def _parse_actions(row: dict) -> dict:
        """
        Extract purchase-related metrics from Meta's nested action arrays.

        Uses .get() with fallbacks throughout (Rule 3).

        Returns:
            dict with keys: purchases, purchase_value, cost_per_purchase,
            adds_to_cart (adds_to_cart only if present in actions).
        """
        actions = row.get("actions", [])
        action_values = row.get("action_values", [])
        cost_per_action = row.get("cost_per_action_type", [])

        purchases = 0
        purchase_value = 0.0
        cost_per_purchase = 0.0
        adds_to_cart = 0

        for action in actions:
            action_type = action.get("action_type", "N/A")
            if action_type == "purchase":
                purchases = int(action.get("value", 0))
            elif action_type == "add_to_cart":
                adds_to_cart = int(action.get("value", 0))

        for av in action_values:
            if av.get("action_type", "N/A") == "purchase":
                purchase_value = float(av.get("value", 0))

        for cpa in cost_per_action:
            if cpa.get("action_type", "N/A") == "purchase":
                cost_per_purchase = float(cpa.get("value", 0))

        return {
            "purchases": purchases,
            "purchase_value": round(purchase_value, 2),
            "cost_per_purchase": round(cost_per_purchase, 2),
            "adds_to_cart": adds_to_cart,
        }

    # ------------------------------------------------------------------
    # Public fetch methods
    # ------------------------------------------------------------------

    def fetch_account_insights(self, date_preset: str = "last_7d") -> dict:
        """
        Pull account-level insights from Meta Graph API.

        Returns a dict of KPIs with safe .get() fallbacks so the pipeline
        survives when campaigns are paused and fields are missing.
        """
        url = f"{self.base_url}/act_{self.ad_account_id}/insights"
        params = {
            "access_token": self.access_token,
            "date_preset": date_preset,
            "fields": ",".join([
                "spend",
                "impressions",
                "clicks",
                "cpm",
                "cpc",
                "ctr",
                "actions",
                "action_values",
                "cost_per_action_type",
            ]),
        }

        payload = self._make_request(url, params)

        data_list = payload.get("data", [])
        data = data_list[0] if data_list else {}

        # --- Safe extraction with .get() and fallbacks (Rule 3) ---
        spend = float(data.get("spend", 0))
        impressions = int(data.get("impressions", 0))
        clicks = int(data.get("clicks", 0))
        cpm = float(data.get("cpm", 0))
        cpc = float(data.get("cpc", 0))
        ctr = float(data.get("ctr", 0))

        parsed = self._parse_actions(data)
        roas = round(parsed["purchase_value"] / spend, 2) if spend > 0 else 0.0
        aov = (
            round(parsed["purchase_value"] / parsed["purchases"], 2)
            if parsed["purchases"] > 0
            else 0.0
        )

        return {
            "spend": round(spend, 2),
            "impressions": impressions,
            "clicks": clicks,
            "cpm": round(cpm, 2),
            "cpc": round(cpc, 2),
            "ctr": round(ctr, 2),
            "purchases": parsed["purchases"],
            "purchase_value": parsed["purchase_value"],
            "cost_per_purchase": parsed["cost_per_purchase"],
            "roas": roas,
            "aov": aov,
            "adds_to_cart": parsed["adds_to_cart"],
        }

    def fetch_campaign_breakdown(self, date_preset: str = "last_7d") -> list[dict]:
        """
        Pull campaign-level insights so the report can reference
        individual campaign performance.
        """
        url = f"{self.base_url}/act_{self.ad_account_id}/insights"
        params = {
            "access_token": self.access_token,
            "date_preset": date_preset,
            "level": "campaign",
            "fields": ",".join([
                "campaign_name",
                "spend",
                "impressions",
                "clicks",
                "cpm",
                "cpc",
                "ctr",
                "actions",
                "action_values",
                "cost_per_action_type",
            ]),
            "limit": 50,
        }

        payload = self._make_request(url, params)

        campaigns = []
        for row in payload.get("data", []):
            campaign_name = row.get("campaign_name", "N/A")
            spend = float(row.get("spend", 0))
            impressions = int(row.get("impressions", 0))
            clicks = int(row.get("clicks", 0))
            cpm = float(row.get("cpm", 0))
            cpc = float(row.get("cpc", 0))
            ctr = float(row.get("ctr", 0))

            parsed = self._parse_actions(row)
            roas = round(parsed["purchase_value"] / spend, 2) if spend > 0 else 0.0

            campaigns.append({
                "campaign_name": campaign_name,
                "spend": round(spend, 2),
                "impressions": impressions,
                "clicks": clicks,
                "cpm": round(cpm, 2),
                "cpc": round(cpc, 2),
                "ctr": round(ctr, 2),
                "purchases": parsed["purchases"],
                "purchase_value": parsed["purchase_value"],
                "cost_per_purchase": parsed["cost_per_purchase"],
                "roas": roas,
            })

        return campaigns

    # ------------------------------------------------------------------
    # CrewAI Agent builder
    # ------------------------------------------------------------------

    def build_agent(self) -> Agent:
        """Return a CrewAI Agent configured for data extraction & analysis."""
        llm = LLM(
            model="openrouter/qwen/qwen3-coder:free",
            api_key=os.environ.get("OPENROUTER_API_KEY"),
            temperature=0.0,  # Rule 2 — strict determinism
            extra_body={
                "models": [
                    "qwen/qwen3-coder:free",
                    "minimax/minimax-m2.5:free",
                ]
            },
        )

        return Agent(
            role="Senior Performance Data Analyst",
            goal=(
                "Fetch raw performance data from the Meta Graph API, "
                "parse every metric safely using .get() with fallbacks, "
                "and produce a structured summary of account-level KPIs "
                "alongside a campaign-level breakdown. "
                "Do NOT interpret or editorialize the numbers — "
                "present them factually."
            ),
            backstory=(
                "You are a meticulous paid-media data analyst with 8 years "
                "of experience pulling numbers from the Meta Ads platform. "
                "You never guess — if a field is missing you surface a "
                "fallback value (0 or 'N/A') and flag it. "
                "You present data in clean, structured tables and never "
                "add opinions or recommendations. Your job ends at the "
                "numbers; someone else writes the narrative."
            ),
            verbose=True,
            allow_delegation=False,
            llm=llm,
            max_rpm=2,           # Throttle to 2 requests/min — avoids upstream 429s
            max_retry_limit=2,   # Controlled retries instead of rapid-fire hammering
        )
