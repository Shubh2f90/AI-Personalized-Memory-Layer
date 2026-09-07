"""
chat_engine.py
Handles talking to the LLM, and the core "memory injection" logic —
this is the actual point of the whole project.

Flow for every message:
1. Pull stored facts about the user (e.g. "user prefers direct answers")
2. Pull recent conversation history
3. Build a system prompt that includes facts as context
4. Send everything to the LLM
5. Save both the user's message and the assistant's reply
6. Every few turns, ask the LLM to extract any new durable facts
"""

import os
from groq import Groq
import memory_db as db

# Reads your API key from the environment variable GROQ_API_KEY
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

MODEL = "openai/gpt-oss-20b"


def build_system_prompt():
    """Construct a system prompt that includes everything we know about the user."""
    facts = db.get_all_facts()

    if not facts:
        return "You are a helpful assistant."

    facts_text = "\n".join(f"- {fact}" for fact in facts)
    return (
        "You are a helpful assistant with memory of this user from past "
        "conversations. Use the following known facts naturally, without "
        "explicitly mentioning that you're using stored memory:\n\n"
        f"{facts_text}"
    )


def get_response(user_message: str) -> str:
    db.save_message("user", user_message)

    system_prompt = build_system_prompt()
    history = db.get_recent_messages(limit=10)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}] + history,
            max_tokens=1000
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"[Error talking to the model: {e}]"

    db.save_message("assistant", reply)

    return reply


def extract_facts_from_conversation():
    """
    Ask the LLM itself to look at recent conversation and extract any new
    durable facts about the user (preferences, goals, skill level, etc).
    This is what makes the system "learn" instead of just storing raw logs.
    """
    history = db.get_recent_messages(10)
    if len(history) < 2:
        return  # not enough conversation yet

    conversation_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in history
    )

    existing_facts = db.get_all_facts()
    existing_text = "\n".join(existing_facts) if existing_facts else "None yet."

    extraction_prompt = f"""Here is a recent conversation:

{conversation_text}

Here are facts already known about the user:
{existing_text}

Extract ONLY new, durable facts about the user worth remembering long-term
(preferences, goals, skill level, ongoing projects, communication style).
Do NOT repeat facts already known. Do NOT include one-off details that
don't matter later.

Reply with each new fact on its own line. If there are no new facts worth
storing, reply with exactly: NONE
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": extraction_prompt}],
            max_tokens=600,
            reasoning_effort="low"
        )
        result = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Fact extraction failed: {e}]")
        return

    if result == "NONE" or not result:
        return

    new_facts = [line.strip("- ").strip() for line in result.split("\n") if line.strip()]
    for fact in new_facts:
        db.save_fact(fact)
        