import os
import sys
import json
from dotenv import load_dotenv
from anthropic import Anthropic

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "rag_pipeline"))
from rag_pipeline import retrieve

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ---------- The actual tool implementations (plain Python) ----------

def search_report(query: str) -> str:
    chunks = retrieve(query, n_results=3)
    return "\n\n".join(chunks)


def calculator(expression: str) -> str:
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


TOOL_FUNCTIONS = {
    "search_report": search_report,
    "calculator": calculator,
}


# ---------- Tool definitions (what Claude sees) ----------

TOOLS = [
    {
        "name": "search_report",
        "description": (
            "Search the company's 10-K filing for information. Use this whenever you "
            "need a fact, figure, or statement that comes from the report itself. "
            "Never guess a number — always retrieve it with this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for, e.g. 'net income' or 'revenue growth'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "calculator",
        "description": (
            "Evaluate a mathematical expression. Use this for ANY arithmetic. "
            "Never compute in your head."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A Python arithmetic expression, e.g. '10100000000 / 2100000000'"
                }
            },
            "required": ["expression"]
        }
    }
]


SYSTEM_PROMPT = """You are a financial analyst assistant with access to a company's 10-K filing.

Rules:
- Use search_report to find any figure from the filing. Never guess a number.
- Use calculator for any arithmetic. Never compute in your head.
- CRITICAL: Whenever you extract a figure from search_report, you MUST quote the
  exact sentence it came from, verbatim, before using it. If you cannot find the
  figure stated explicitly in the retrieved text, say so instead of inferring it.
- State clearly which figures you retrieved, what you quoted, and what you calculated."""

# ---------- The Agent Loop ----------

def run_agent(question, max_iterations=5):
    messages = [{"role": "user", "content": question}]

    for i in range(max_iterations):
        print(f"\n--- Iteration {i + 1} ---")

        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        print(f"[stop_reason] {response.stop_reason}")

        # Claude is done — return the final text
        if response.stop_reason == "end_turn":
            return response.content[0].text

        # Claude wants to use tool(s)
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"[TOOL CALL] {block.name}({block.input})")

                    func = TOOL_FUNCTIONS[block.name]
                    output = func(**block.input)

                    print(f"[TOOL RESULT] {output}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output
                    })

            messages.append({"role": "user", "content": tool_results})

    return "Max iterations reached without a final answer."


# ---------- Run ----------

if __name__ == "__main__":
    question = (
        "What is the EPS if net income is the figure from the report "
        "and shares outstanding are 2.1 billion?"
    )

    print(f"=== Question: {question} ===")
    answer = run_agent(question)

    print(f"\n=== Final Answer ===")
    print(answer)