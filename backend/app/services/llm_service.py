import anthropic
from starlette.concurrency import run_in_threadpool

SYSTEM_PROMPT = """\
You are writing a personal memoir on behalf of a storyteller, based \
strictly on their own recorded answers to guided life-story questions. \
You will be given a series of questions grouped into chapters, each with \
the storyteller's own answer.

Rules that must never be broken:
- Only use facts, names, dates, and events that appear explicitly in the \
provided answers. Do not invent, infer, guess, or embellish any detail \
that isn't stated.
- Do not fill gaps with generic or plausible-sounding content. If a \
chapter has no answers, omit that chapter entirely — do not write a \
placeholder for it.
- You may rephrase, reorder, and connect answers into flowing prose, add \
narrative transitions, and write in first person as the storyteller — \
but every factual claim must trace back to something they actually said.

Output format: plain markdown. A single "# " line with a fitting book \
title. Then one "## " heading per chapter (using the chapter names \
given), each followed by flowing narrative paragraphs woven from that \
chapter's answers.
"""


def _build_user_message(account_name: str, entries: list[tuple[str, str, str]]) -> str:
    lines = [f"Storyteller's account name: {account_name}", ""]
    current_chapter = None
    for chapter, question, answer in entries:
        if chapter != current_chapter:
            lines.append(f"## Chapter: {chapter}")
            current_chapter = chapter
        lines.append(f"Q: {question}")
        lines.append(f"A: {answer}")
        lines.append("")
    return "\n".join(lines)


def _generate_sync(account_name: str, entries: list[tuple[str, str, str]]) -> str:
    client = anthropic.Anthropic()
    with client.messages.stream(
        model="claude-opus-4-8",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": _build_user_message(account_name, entries),
            }
        ],
    ) as stream:
        message = stream.get_final_message()
    return next(block.text for block in message.content if block.type == "text")


async def generate_memoir_text(
    account_name: str, entries: list[tuple[str, str, str]]
) -> str:
    """Turns (chapter, question, answer) entries into a markdown memoir.

    The only function that talks to Claude — isolates the API call the
    same way transcription_service.py isolates the Whisper call.
    """
    return await run_in_threadpool(_generate_sync, account_name, entries)
