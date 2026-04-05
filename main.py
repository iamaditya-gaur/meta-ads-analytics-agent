"""
main.py — Orchestrates the Meta Ads Reporting Crew.

Responsibilities:
  • Loads environment variables via python-dotenv (Rule 5)
  • Instantiates agents and fetches data
  • Creates tasks and runs the crew sequentially
  • Output is saved to client_report.md by CrewAI's output_file parameter
"""

import os
import sys
from dataclasses import dataclass
from dotenv import load_dotenv

# Rule 5 — load .env before any API keys are accessed or agents are imported
load_dotenv()

from crewai import Crew, Process

from agents.data_analyst_agent import (
    DataAnalystAgent,
    MetaTokenExpiredError,
    MetaAPIError,
)
from agents.comms_lead_agent import CommsLeadAgent
from tasks.extraction_tasks import create_extraction_task
from tasks.writing_tasks import create_writing_task


@dataclass(frozen=True)
class RunConfig:
    """Immutable runtime configuration for a single crew execution."""

    client_name: str = "Coffee Beanery"
    report_period: str = "Mar 22 - Mar 29"
    date_preset: str = "last_7d"


def _load_config() -> RunConfig:
    """Build a RunConfig from environment variables with sensible defaults."""
    return RunConfig(
        client_name=os.environ.get("CLIENT_NAME", RunConfig.client_name),
        report_period=os.environ.get("REPORT_PERIOD", RunConfig.report_period),
        date_preset=os.environ.get("DATE_PRESET", RunConfig.date_preset),
    )


def _validate_env() -> None:
    """Ensure all required environment variables are present."""
    required_vars = [
        "META_ACCESS_TOKEN",
        "META_AD_ACCOUNT_ID",
        "OPENROUTER_API_KEY",
    ]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("   Please set them in your .env file and try again.")
        sys.exit(1)


def main(config: RunConfig | None = None):
    # ------------------------------------------------------------------
    # 1. Validate environment & load config
    # ------------------------------------------------------------------
    _validate_env()
    if config is None:
        config = _load_config()

    # ------------------------------------------------------------------
    # 2. Instantiate agents
    # ------------------------------------------------------------------
    data_analyst = DataAnalystAgent()
    comms_lead = CommsLeadAgent()

    analyst_agent = data_analyst.build_agent()
    writer_agent = comms_lead.build_agent()

    # ------------------------------------------------------------------
    # 3. Fetch data from Meta Graph API
    # ------------------------------------------------------------------
    try:
        print("📡 Fetching account-level insights from Meta…")
        account_data = data_analyst.fetch_account_insights(
            date_preset=config.date_preset
        )
        print(
            f"   ✅ Account data retrieved — "
            f"Spend: ${account_data.get('spend', 0):,.2f}"
        )

        print("📡 Fetching campaign-level breakdown…")
        campaign_data = data_analyst.fetch_campaign_breakdown(
            date_preset=config.date_preset
        )
        print(f"   ✅ {len(campaign_data)} campaign(s) retrieved")

    except MetaTokenExpiredError as e:
        print(f"\n🛑 {e}")
        sys.exit(1)
    except MetaAPIError as e:
        print(f"\n⚠️  {e}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 4. Create tasks
    # ------------------------------------------------------------------
    extraction_task = create_extraction_task(
        agent=analyst_agent,
        account_data=account_data,
        campaign_data=campaign_data,
    )

    writing_task = create_writing_task(
        agent=writer_agent,
        extraction_task=extraction_task,
        client_name=config.client_name,
        report_period=config.report_period,
    )

    # ------------------------------------------------------------------
    # 5. Assemble and run the crew
    # ------------------------------------------------------------------
    crew = Crew(
        agents=[analyst_agent, writer_agent],
        tasks=[extraction_task, writing_task],
        process=Process.sequential,
        verbose=True,
    )

    print("\n🚀 Kicking off the Meta Ads Reporting Crew…\n")
    result = crew.kickoff()

    # ------------------------------------------------------------------
    # 6. Output the final report
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("📋 FINAL CLIENT REPORT")
    print("=" * 60)
    print(result)
    print("=" * 60)
    print("\n💾 Report saved to client_report.md")


if __name__ == "__main__":
    main()
