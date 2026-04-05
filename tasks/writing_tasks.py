"""
Writing Tasks — defines CrewAI Task objects for report generation.

These tasks are assigned to the Comms Lead agent and depend on the
output of the extraction task.
"""

from crewai import Task, Agent


def create_writing_task(
    agent: Agent,
    extraction_task: Task,
    client_name: str,
    report_period: str,
) -> Task:
    """
    Build a Task that instructs the Comms Lead agent to convert
    the structured data summary into a client-facing report.

    Parameters
    ----------
    agent : Agent
        The Comms Lead CrewAI agent.
    extraction_task : Task
        The upstream extraction task whose output is consumed here.
    client_name : str
        The brand / client handle (e.g., "lectron fuel systems").
    report_period : str
        Human-readable period string (e.g., "Mar 22 - Mar 29").

    Returns
    -------
    Task
    """
    description = (
        f"Using the structured data summary provided by the Data Analyst, "
        f"write a client-facing performance update for @{client_name} "
        f"covering the period {report_period}.\n\n"
        "MANDATORY FORMAT RULES:\n"
        '1. Open with "Hey @{client_name}, last week on Meta ({period})…" '
        "matching the tone reference exactly.\n"
        "2. Cite specific numbers: spend, ROAS, CPP, and any notable "
        "campaign-level call-outs.\n"
        "3. Include percentage changes from prior period if available.\n"
        "4. Reference specific campaign names and tactical moves "
        "(bid strategy changes, new launches, budget shifts).\n"
        "5. Keep the update to 1-3 short paragraphs — matching the "
        "length and density of the tone reference examples.\n"
        "6. Do NOT use any generic AI filler words such as: "
        '"delve," "moreover," "in summary," "furthermore," '
        '"it is worth noting," "leveraging," "utilizing."\n'
        "7. End naturally — no sign-off, footer, or disclaimer.\n"
    ).format(client_name=client_name, period=report_period)

    return Task(
        description=description,
        expected_output=(
            "A polished, 1-3 paragraph client-facing Meta Ads performance "
            "update that mirrors the tone, vocabulary, and formatting of "
            "the tone reference. Every metric must be sourced from the "
            "data summary — no fabricated numbers."
        ),
        agent=agent,
        context=[extraction_task],
        output_file="client_report.md",
    )
