# ============================================================
# SAKILA AI AGENT
# Claude + Tool Layer
# ============================================================

import os
import json
import anthropic

from dotenv import load_dotenv

from tools.tool_definitions import (
    TOOL_DEFINITIONS,
    TOOL_FUNCTIONS
)


# ============================================================
# 1. CONFIG
# ============================================================

load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not API_KEY:
    print("ERROR: ANTHROPIC_API_KEY not found.")
    exit()

client = anthropic.Anthropic(
    api_key=API_KEY
)

MODEL = "claude-sonnet-4-5"


# ============================================================
# 2. SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are Sakila AI Analyst.

You are an AI pricing and elasticity analyst
working with Sakila rental data.

Your job is to answer questions about:

- price elasticity
- category performance
- statistical significance
- demand
- revenue
- price changes
- pricing recommendations

You have access to multiple analytical tools.

IMPORTANT RULES:

1. Use tools when the user's question requires
   actual elasticity or business data.

2. Do not invent numerical results.

3. Use multiple tools when necessary.

4. If a tool result is insufficient, call another
   appropriate tool.

5. Consider statistical significance before making
   pricing recommendations.

6. Explain the reasoning behind recommendations.

7. Answer in Vietnamese unless the user asks
   for another language.

8. Keep answers clear and business-oriented.
"""


# ============================================================
# 3. TOOL EXECUTION
# ============================================================

def execute_tool(tool_name, tool_input):

    """
    Execute a Python tool from TOOL_FUNCTIONS.
    """

    if tool_name not in TOOL_FUNCTIONS:

        return {
            "error": f"Unknown tool: {tool_name}"
        }

    function = TOOL_FUNCTIONS[tool_name]

    try:

        result = function(**tool_input)

        return result

    except Exception as e:

        return {
            "error": (
                f"Tool '{tool_name}' failed: "
                f"{str(e)}"
            )
        }


# ============================================================
# 4. CLAUDE AGENT LOOP
# ============================================================

def ask_claude(user_question):

    """
    Send a question to Claude and allow Claude
    to use multiple tools until it can produce
    a final answer.
    """

    messages = [

        {
            "role": "user",
            "content": user_question
        }

    ]

    # --------------------------------------------------------
    # Agent loop
    # --------------------------------------------------------

    while True:

        response = client.messages.create(

            model=MODEL,

            max_tokens=2048,

            system=SYSTEM_PROMPT,

            messages=messages,

            tools=TOOL_DEFINITIONS
        )

        # ----------------------------------------------------
        # If Claude wants to use tools
        # ----------------------------------------------------

        if response.stop_reason == "tool_use":

            # Add Claude's response to conversation

            messages.append({

                "role": "assistant",

                "content": response.content
            })

            tool_results = []

            # ------------------------------------------------
            # Process every tool Claude requested
            # ------------------------------------------------

            for block in response.content:

                if block.type != "tool_use":
                    continue

                tool_name = block.name

                tool_input = block.input

                print(
                    f"\n[Agent] Calling tool: "
                    f"{tool_name}"
                )

                print(
                    f"[Agent] Input: "
                    f"{tool_input}"
                )

                # Execute Python function

                result = execute_tool(
                    tool_name,
                    tool_input
                )

                print(
                    f"[Agent] Tool completed."
                )

                # Make sure result is JSON serializable

                try:

                    result_json = json.dumps(
                        result,
                        ensure_ascii=False
                    )

                except TypeError:

                    result_json = json.dumps(
                        {
                            "error":
                                "Tool result is not JSON serializable."
                        },
                        ensure_ascii=False
                    )

                tool_results.append({

                    "type": "tool_result",

                    "tool_use_id":
                        block.id,

                    "content":
                        result_json
                })

            # ------------------------------------------------
            # Send tool results back to Claude
            # ------------------------------------------------

            messages.append({

                "role": "user",

                "content": tool_results
            })

            # Continue loop

            continue

        # ----------------------------------------------------
        # Claude has finished
        # ----------------------------------------------------

        final_text = []

        for block in response.content:

            if hasattr(block, "text"):

                final_text.append(
                    block.text
                )

        return "\n".join(final_text)


# ============================================================
# 5. TERMINAL INTERFACE
# ============================================================

def main():

    print("=" * 70)

    print(
        "SAKILA PRICE ELASTICITY AI ANALYST"
    )

    print("=" * 70)

    print(
        "\nAsk questions about elasticity, "
        "revenue and pricing."
    )

    print(
        "Claude can use multiple analytical tools."
    )

    print(
        "\nType 'exit' to quit.\n"
    )

    while True:

        try:

            user_question = input("You: ")

        except KeyboardInterrupt:

            print("\nGoodbye.")

            break

        except EOFError:

            print("\nGoodbye.")

            break

        # ----------------------------------------------------
        # Exit
        # ----------------------------------------------------

        if user_question.lower().strip() in [
            "exit",
            "quit"
        ]:

            print("Goodbye.")

            break

        # ----------------------------------------------------
        # Empty input
        # ----------------------------------------------------

        if not user_question.strip():

            continue

        # ----------------------------------------------------
        # Ask Claude
        # ----------------------------------------------------

        try:

            answer = ask_claude(
                user_question
            )

            print("\nClaude:")
            print(answer)
            print()

        except Exception as e:

            print(
                "\nClaude API error:"
            )

            print(e)

            print()


# ============================================================
# 6. RUN
# ============================================================

if __name__ == "__main__":

    main()
