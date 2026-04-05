"""
Comms Lead Agent — transforms raw data into a client-facing report
that mirrors the exact tone, vocabulary, and formatting found in
tone_context.txt.

Architectural rules enforced:
  • temperature=0.0  (strict determinism)
  • Reads tone_context.txt at build time and injects it into the backstory
  • Explicitly forbidden from using AI filler words
"""

import os
from crewai import Agent, LLM


class CommsLeadAgent:
    """Encapsulates the Communications Lead agent."""

    # Words and phrases the agent must NEVER use (Rule 4)
    BANNED_WORDS = [
        "delve", "moreover", "in summary", "furthermore",
        "it is worth noting", "it's important to note",
        "in conclusion", "as a matter of fact", "needless to say",
        "leveraging", "utilizing", "landscape", "paradigm",
        "synergy", "holistic", "robust",
    ]

    def __init__(self, tone_context_path: str = "tone_context.txt"):
        """
        Load the tone reference file so it can be injected
        verbatim into the agent backstory.
        """
        resolved_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            tone_context_path,
        )
        if not os.path.isfile(resolved_path):
            raise FileNotFoundError(
                f"Tone context file not found: {resolved_path}\n"
                "Ensure tone_context.txt exists in the project root."
            )
        with open(resolved_path, "r", encoding="utf-8") as f:
            self.tone_context = f.read()

    def build_agent(self) -> Agent:
        """Return a CrewAI Agent configured for report writing."""
        llm = LLM(
            model="openrouter/arcee-ai/trinity-large-preview:free",
            api_key=os.environ.get("OPENROUTER_API_KEY"),
            temperature=0.0,  # Rule 2 — strict determinism
            extra_body={
                "models": [
                    "arcee-ai/trinity-large-preview:free",
                    "qwen/qwen3-next-80b-a3b-instruct:free",
                ]
            },
        )

        banned_list = ", ".join(f'"{w}"' for w in self.BANNED_WORDS)

        backstory = (
            "You are the Communications Lead responsible for writing "
            "weekly and monthly Meta Ads performance updates that are sent "
            "directly to clients. Your writing must be indistinguishable "
            "from the examples below.\n\n"
            "=== TONE REFERENCE (mirror this exactly) ===\n"
            f"{self.tone_context}\n"
            "=== END TONE REFERENCE ===\n\n"
            "STRICT STYLE RULES:\n"
            "1. Match the sentence length, paragraph structure, and "
            "vocabulary of the tone reference EXACTLY.\n"
            "2. Use the same casual-professional greeting format "
            '(e.g., "Hey @brand name, last week on Meta…").\n'
            "3. Reference specific campaign names, bid strategies, "
            "and tactical changes just like the examples do.\n"
            "4. Include percentage changes from the prior period "
            "where available.\n"
            "5. Keep insights grounded in data — no vague praise.\n"
            f"6. NEVER use these words or phrases: {banned_list}.\n"
            "7. Do NOT add any sign-off, footer, or disclaimer. "
            "End the update naturally, the way the examples do."
        )

        return Agent(
            role="Client Communications Lead",
            goal=(
                "Take the structured performance data handed to you and "
                "write a polished client-facing report that perfectly "
                "mirrors the tone, vocabulary, sentence length, and "
                "formatting found in the tone reference. Every number "
                "cited must come from the data — do not fabricate metrics."
            ),
            backstory=backstory,
            verbose=True,
            allow_delegation=False,
            llm=llm,
            max_rpm=2,           # Throttle to 2 requests/min — avoids upstream 429s
            max_retry_limit=2,   # Controlled retries instead of rapid-fire hammering
        )
