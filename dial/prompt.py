"""Shared proposal prompt. Training and the local runner use the same text."""

from dial.bars import bar_lines

RULE = (
    "Propose one FSOT expression using engine names and integer powers. "
    "Do not invent a decimal coefficient. "
    "The engine computes the value. A published uncertainty scores it. "
    "Lean accepts or rejects a formal statement. "
    "Reply with one line: PROPOSAL: <expression>"
)


def proposal_prompt(row: dict) -> str:
    return "\n".join(
        [
            RULE,
            f"DOMAIN: {row.get('domain')}",
            f"NAME: {row.get('name')}",
            f"PROPERTY: {row.get('property')}",
            f"MEASURED: {row.get('measured')}",
            *bar_lines(row),
        ]
    )


def proposal_target(formula: str) -> str:
    return f"PROPOSAL: {formula}"


RECORD_USER = "Repeat the recorded FSOT statement. Do not invent a coefficient."


def chat_example(user: str, assistant: str) -> dict:
    """One Gemma 4 turn. Thinking stays off. The assistant text is the training target."""
    return {
        "prompt": [{"role": "user", "content": user}],
        "completion": [{"role": "assistant", "content": assistant}],
        "chat_template_kwargs": {"enable_thinking": False},
    }
