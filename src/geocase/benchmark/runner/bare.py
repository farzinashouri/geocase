"""Track A — bare: one single-shot completion per task, no tools, no loop.

Runs on every model and is maximally comparable. The prompt asks for exactly
one fenced python block; an unparseable reply records MISSING with
``detail: no code block``."""

from __future__ import annotations

from dataclasses import dataclass

from geocase.benchmark.prompts import task_paragraph
from geocase.benchmark.registry import TaskMeta
from geocase.benchmark.runner.extract import extract_code_block
from geocase.benchmark.runner.openrouter import ChatReply, OpenRouterClient

BARE_TEMPLATE = """You are writing one small self-contained Python module.

{paragraph}

Requirements:
- You may use the standard library plus any of: shapely 2.1, pyproj 3.7, rasterio 1.4, numpy, scikit-learn.
- Importing the module must have no side effects.
- Reply with exactly one fenced ```python code block containing the complete module, and nothing else after it.
"""


def bare_prompt(task: TaskMeta) -> str:
    return BARE_TEMPLATE.format(paragraph=task_paragraph(task))


@dataclass
class BareResult:
    task: str
    content: str
    code: str | None
    cost: float | None
    usage: dict


def run_bare_task(
    client: OpenRouterClient,
    model_id: str,
    task: TaskMeta,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> BareResult:
    reply: ChatReply = client.chat(
        model_id,
        [{"role": "user", "content": bare_prompt(task)}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return BareResult(
        task=task.name,
        content=reply.content,
        code=extract_code_block(reply.content),
        cost=reply.cost,
        usage=reply.usage,
    )
