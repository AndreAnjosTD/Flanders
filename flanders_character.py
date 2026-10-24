#!/usr/bin/env python3
"""
Flanders Character - A task delegate inspired by Ned Flanders from The Simpsons.
Allows the captain to talk to Flanders and delegate tasks to agents/sub-agents.
"""

import json
import sys
import os
from pathlib import Path

# Add the Flanders project skills to the path
sys.path.insert(0, str(Path(__file__).parent / ".agents" / "skills"))


def flanders_response(task_description):
    """
    Process a task using the Flanders skill approach.
    Returns a Flanders-style response with task delegation guidance.
    """
    # Flanders-inspired task classification
    task_lower = task_description.lower()

    responses = {
        "feature": {
            "prefix": "Okily dokily! ",
            "middle": "Let me help you think through implementing that feature, kind user!",
            "suffix": "We could ship this as a no-mistakes PR, or take a quick ship approach depending on your posture preference.",
        },
        "bug": {
            "prefix": "Thank you, kind user! ",
            "middle": "Bugs are quite the predicament, but fear not! I'll help you analyze what needs fixing.",
            "suffix": "We'll patch this up right proper-like, and the Lord willing, it'll be good as new!",
        },
        "pr": {
            "prefix": "Praise the Lord! ",
            "middle": "A PR ready for review! Let me think through the yolo posture and delivery mode.",
            "suffix": "Whether we go no-mistakes or direct-PR, I'll make sure the merge is shipshape.",
        },
        "default": {
            "prefix": "Okily dokily! ",
            "middle": "I'm your faithful task delegate, and I'm here to help you offload your godly tasks!",
            "suffix": "Just tell me what you're working on and I'll help you think through the best way to delegate it!",
        },
    }

    # Classify the task type
    if any(word in task_lower for word in ["feature", "implement", "code", "build"]):
        r = responses["feature"]
    elif any(word in task_lower for word in ["bug", "fix", "repair", "error"]):
        r = responses["bug"]
    elif any(word in task_lower for word in ["pr", "pull request", "review", "merge"]):
        r = responses["pr"]
    else:
        r = responses["default"]

    return (
        f"{r['prefix']}{r['middle']}\n\n"
        f"{r['suffix']}\n\n"
        "---\n\n"
        "I can help you classify the work as ship/scout, consider the yolo posture, "
        "think about delivery modes (no-mistakes, direct-PR, or local-only), and create "
        "proper briefs using the task brief scaffold!"
    )


def delegate_task(task_description, target_agent=None):
    """
    Delegate a task to an agent or sub-agent.
    In a full implementation, this would integrate with Firstmate's crew/scout system.
    """
    delegation = {
        "task": task_description,
        "delegate": "Flanders",
        "personality": "Ned Flanders (The Simpsons)",
        "phrasing": "Okily dokily!",
        "classification": classify_task(task_description),
        "delivery_modes": ["no-mistakes", "direct-PR", "local-only"],
        "yolo_options": ["with merge authority", "without merge authority"],
        "status": "pending_delegation",
    }

    if target_agent:
        delegation["target_agent"] = target_agent
        delegation["message"] = f"Delegating to {target_agent}: {task_description}"
    else:
        delegation["message"] = f"Task queued for delegation: {task_description}"

    return delegation


def classify_task(task_description):
    """Classify the task into a delivery mode category."""
    task_lower = task_description.lower()

    if any(word in task_lower for word in ["safety-critical", "production", "no-mistakes"]):
        return "no-mistakes"
    elif any(word in task_lower for word in ["quick", "fast", "direct"]):
        return "direct-PR"
    else:
        return "local-only"


def main():
    """Main entry point for interacting with Flanders."""
    print("=" * 60)
    print("  FLANDERS - Your Godly Task Delegate")
    print("=" * 60)
    print()
    print("Hi-diddly-ho, investorino! Welcome to Flanders' task delegation station!")
    print("I'm listening and ready to help you delegate your godly tasks.")
    print("Use 'Okily dokily!' to start, or just tell me what you need done.")
    print()
    print("Commands:")
    print("  /help       - Show this help message")
    print("  /delegate   - Delegate a task to an agent")
    print("  /status     - Check task status")
    print("  /quit       - Exit Flanders' station")
    print()
    print("-" * 60)

    while True:
        try:
            user_input = input("\n> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["/quit", "exit", "q"]:
                print(
                    "\nOkily dokily! May the Lord watch over your tasks until next we meet!"
                )
                break

            elif user_input.lower() in ["/help", "help"]:
                print("\nFlanders' Command Guide:")
                print("  /delegate <task>    - Delegate a task for analysis")
                print("  /status             - Check current task status")
                print("  /modes              - Show delivery mode options")
                print("  /quit               - Exit Flanders' station")
                print()

            elif user_input.lower() in ["/modes", "modes"]:
                print("\nDelivery Mode Options:")
                print("  1. no-mistakes  - Full pipeline through PR, then merge authority wait")
                print("  2. direct-PR    - Push and open PR without no-mistakes pipeline")
                print("  3. local-only   - Stop with ready branch, wait for merge authority landing")
                print()

            elif user_input.lower().startswith("/delegate"):
                task = user_input[len("/delegate") :].strip()
                if task:
                    print("\n" + "=" * 60)
                    print("Flanders is thinking through your task...")
                    print("=" * 60 + "\n")

                    # Classify and delegate
                    classification = classify_task(task)
                    delegation = delegate_task(task)

                    print(f"📋 Task Classification: {classification}")
                    print(f"📝 Task: {task}")
                    print(f"🙍‍♂️ Delegate: Flanders")
                    print(f"💬 Phrasing: {delegation['phrasing']}")
                    print()
                    print(flanders_response(task))
                    print()
                    print("Okily dokily! I've noted your task and will help you delegate it properly!")
                else:
                    print("\nPlease provide a task to delegate after /delegate command.")
                    print(
                        "Example: /delegate 'Implement user authentication feature'"
                    )

            else:
                # General task conversation
                print("\n" + "=" * 60)
                print("Flanders is considering your request...")
                print("=" * 60 + "\n")
                print(flanders_response(user_input))
                print()
                print("Okily dokily! What else can Flanders help you with, kind user?")

        except KeyboardInterrupt:
            print(
                "\n\nOkily dokily! May the Lord watch over your tasks until next we meet!"
            )
            break
        except Exception as e:
            print(f"\nAw, hamburgers! Something went wrong: {e}")
            print("Flanders is still learning, but he'll do his best!")


if __name__ == "__main__":
    main()