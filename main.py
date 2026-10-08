"""
main.py
Simple command-line interface to interact with the memory-enabled chatbot.

Run this file, talk to it, exit, run it again — it should remember
facts from your previous session without you repeating yourself.
"""

import os
import memory_db as db
import chat_engine as engine

TURN_COUNT_BEFORE_EXTRACTION = 3  # extract facts every N user turns


def main():
    """Run the chat loop: talk, extract facts every few turns, save on exit."""
    if not os.environ.get("GROQ_API_KEY"):
        print('GROQ_API_KEY is not set. In PowerShell run:')
        print('  $env:GROQ_API_KEY="your-key"')
        return

    db.init_db()

    print("=" * 50)
    print("AI Memory Layer — type 'exit' to quit")
    print("=" * 50)

    existing_facts = db.get_all_facts()
    if existing_facts:
        print(f"\n(Loaded {len(existing_facts)} known facts about you)\n")

    turn_count = 0

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            user_input = "exit"

        if user_input.lower() in ("exit", "quit"):
            print("\nSaving memory before exit...")
            engine.extract_facts_from_conversation()
            print("Goodbye!")
            break

        if not user_input:
            continue

        reply = engine.get_response(user_input)
        print(f"\nAssistant: {reply}")

        turn_count += 1
        if turn_count % TURN_COUNT_BEFORE_EXTRACTION == 0:
            engine.extract_facts_from_conversation()


if __name__ == "__main__":
    main()