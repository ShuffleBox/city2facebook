import json
import logging
import re
import sys
import time

from openai import OpenAI


logger = logging.getLogger("fbpost")


SYSTEM_PROMPT = """You are Dentron 3000, an AI that summarizes Denton, TX city government meetings for a Facebook page.

You are a concerned citizen who wants what is best for the city and the people who live in it. You are generally positive and constructive about city happenings, highlighting community benefits and progress. However, you do not shy away from noting when decisions seem questionable, controversial, or potentially harmful to residents. You stay factual and avoid partisan language.

Your summaries should be accessible to everyday residents -- no bureaucratic jargon without explanation. You focus on what impacts people's lives: taxes, fees, construction, safety, parks, schools, housing, roads, etc.

Include as much relevant detail as the meeting warrants. There is no length limit.

You must output a valid JSON object with exactly these fields:
- "summary": A factual overview of the meeting
- "key_decisions": A list of bullet points covering all the main votes, resolutions, and actions taken
- "impactful_events": A list of items that notably affect residents (new fees, policy changes, development approvals, safety measures, etc.). Use null if nothing impactful.
- "anecdote": A brief lighthearted or community-positive moment from the meeting, if any. Use null if there was nothing notable."""


def build_user_prompt(meeting) -> str:
    parts = []
    parts.append(f"Meeting Body: {meeting.body_name}")
    parts.append(f"Date: {meeting.date}")
    parts.append(f"Title: {meeting.title}")
    parts.append("")
    parts.append("=== AGENDA CHAPTERS ===")
    parts.append(meeting.get_agenda_summary())
    parts.append("")

    if meeting.agenda_text:
        agenda = meeting.agenda_text[:8000]
        parts.append("=== AGENDA DOCUMENT TEXT ===")
        parts.append(agenda)
        parts.append("")

    transcript = meeting.transcript
    parts.append("=== MEETING TRANSCRIPT ===")
    parts.append(transcript)

    parts.append("")
    parts.append("Please produce a JSON summary of this meeting.")

    return "\n".join(parts)


def summarize(meeting, config: dict) -> dict:
    prompt = build_user_prompt(meeting)
    logger.debug(f"Prompt size: {len(prompt)} chars")

    logger.info(f"Connecting to LLM at {config['llm_base_url']}...")
    logger.debug(f"Model: {config['llm_model']}")
    client = OpenAI(
        api_key=config["llm_key"],
        base_url=config["llm_base_url"],
        timeout=600.0,
    )

    t0 = time.time()
    response = client.chat.completions.create(
        model=config["llm_model"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=8192,
    )
    elapsed = time.time() - t0

    raw = response.choices[0].message.content.strip()
    logger.info(f"LLM generation complete in {elapsed:.1f}s")

    if response.usage:
        usage = response.usage
        logger.debug(f"Token usage: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")

    parsed = parse_json(raw)
    return parsed


def parse_json(raw: str) -> dict:
    logger.debug("Parsing LLM JSON output...")
    raw = raw.strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group()
    try:
        result = json.loads(raw)
        logger.info("JSON parsed successfully.")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"LLM output is not valid JSON: {e}")
        print("Warning: LLM output is not valid JSON. Raw output:")
        print(raw)
        sys.exit(1)
