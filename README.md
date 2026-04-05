Hey there 👋, here’s a look at the Meta Ads Analytics Agent I recently built to automate campaign reporting on Meta:

## Project Mechanics
* **The Motivation**: We needed a reliable way to automate our analytics process seamlessly across varying timelines, whether that’s a weekly check-in or a comprehensive monthly report.
* **Data Analyst Agent**: This agent fetches raw Meta API data and standardizes it.
* **Comms Lead Agent**: Takes that structured data and writes updates perfectly matching our brand voice.
* **Execution Setup**: We're running this through OpenRouter using their open-source models. To keep things stable and ensure we don't trip over rate limits from OpenRouter's free tiers, I’ve set a strict `max_rpm` limit on the LLMs. Both agents also operate at a 0.0 temperature constraint to lock down the precise tone and guarantee zero-hallucination output.

## Performance Insights
* **Clean Data Pipeline**: The first agent connects to the Meta Graph API via token, pulls active campaigns, and organizes metrics like spend, ROAS, varying CPPs, and total purchases. It explicitly relies on safe fallbacks so the pipeline stays robust even when ads are paused or fields run empty.
* **Premium Output Formatting**: The structured numbers are then handed directly to our Comms Lead. Coupled with a strict tone reference, the agent writes the final client-facing report. This eliminates generic AI filler words and produces updates that sound human, data-grounded, and instantly ready for distribution.
* **Security Measures**: We rely entirely on environment variables for all sensitive keys (Meta tokens, LLM keys). They aren't stored in the repo, ensuring we don’t leak anything critical when pushing to GitHub.

If you want to replicate this setup, just populate your local `.env` and execute `python main.py`.
