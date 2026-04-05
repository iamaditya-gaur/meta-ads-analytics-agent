"""
Extraction Tasks — defines CrewAI Task objects for data fetching
and structuring.

These tasks are assigned to the Data Analyst agent.
"""

from crewai import Task, Agent


def create_extraction_task(
    agent: Agent,
    account_data: dict,
    campaign_data: list[dict],
) -> Task:
    """
    Build a Task that instructs the Data Analyst agent to organize
    pre-fetched Meta Ads data into a structured performance summary.

    Parameters
    ----------
    agent : Agent
        The Data Analyst CrewAI agent.
    account_data : dict
        Account-level KPIs returned by DataAnalystAgent.fetch_account_insights().
    campaign_data : list[dict]
        Campaign-level rows from DataAnalystAgent.fetch_campaign_breakdown().

    Returns
    -------
    Task
    """
    campaign_lines = ""
    for c in campaign_data:
        campaign_lines += (
            f"  - {c.get('campaign_name', 'N/A')}: "
            f"Spend ${c.get('spend', 0):,.2f} | "
            f"Purchases {c.get('purchases', 0)} | "
            f"CPP ${c.get('cost_per_purchase', 0):,.2f} | "
            f"ROAS {c.get('roas', 0):.2f}x | "
            f"CPM ${c.get('cpm', 0):,.2f} | "
            f"CPC ${c.get('cpc', 0):,.2f} | "
            f"CTR {c.get('ctr', 0):.2f}%\n"
        )

    description = (
        "You have been given the following pre-fetched Meta Ads data.\n\n"
        "ACCOUNT-LEVEL SUMMARY:\n"
        f"  Ad Spend: ${account_data.get('spend', 0):,.2f}\n"
        f"  Impressions: {account_data.get('impressions', 0):,}\n"
        f"  Clicks: {account_data.get('clicks', 0):,}\n"
        f"  CPM: ${account_data.get('cpm', 0):,.2f}\n"
        f"  CPC: ${account_data.get('cpc', 0):,.2f}\n"
        f"  CTR: {account_data.get('ctr', 0):.2f}%\n"
        f"  Purchases: {account_data.get('purchases', 0)}\n"
        f"  Purchase Value: ${account_data.get('purchase_value', 0):,.2f}\n"
        f"  Cost Per Purchase: ${account_data.get('cost_per_purchase', 0):,.2f}\n"
        f"  ROAS: {account_data.get('roas', 0):.2f}x\n"
        f"  AOV: ${account_data.get('aov', 0):,.2f}\n"
        f"  Adds to Cart: {account_data.get('adds_to_cart', 0):,}\n\n"
        "CAMPAIGN-LEVEL BREAKDOWN:\n"
        f"{campaign_lines}\n"
        "Organize this data into a clean, factual performance summary. "
        "Do NOT add opinions, recommendations, or narrative. "
        "Present the numbers exactly as given, formatted for easy reading."
    )

    return Task(
        description=description,
        expected_output=(
            "A structured performance summary containing:\n"
            "1. An account-level KPI table with all metrics listed.\n"
            "2. A campaign-level breakdown table.\n"
            "All numbers must match the source data exactly."
        ),
        agent=agent,
    )
