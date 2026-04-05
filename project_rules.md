Project Architecture & Strict Rules
Core Objective
We are building a CrewAI application to fetch Meta Ads data and generate a deterministically styled client report.

Architectural Rules (Non-Negotiable)
1. Modularity: All agents must be defined as classes in their respective files within the /agents directory. All tasks must be defined in the /tasks directory.

2. Strict Determinism: Every LLM instantiation for any agent MUST have temperature=0.0. Do not allow creative liberties with data or tone.

3. Meta API Safety Protocol: The data_analyst_agent.py must use the requests library to hit the Meta Graph API. When parsing the JSON payload, it is strictly forbidden to use direct key access (e.g., data['spend']). You MUST use the .get() method with a fallback of 0 or "N/A" (e.g., data.get('spend', 0)). This ensures the pipeline survives if ads are paused and fields are missing.

4. Tone Adherence: The comms_lead_agent.py must be explicitly instructed in its backstory to read tone_context.txt from the root directory and perfectly mirror the sentence length, vocabulary, and formatting. It must NOT use generic AI filler words (e.g., "delve," "moreover," "in summary").

5. Environment Variables: Use python-dotenv in main.py to load credentials. Never hardcode API keys.
