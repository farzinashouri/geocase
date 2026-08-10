"""Task discovery and validation.

A task is a directory under ``tasks/`` holding ``task.yaml`` (validated
against :class:`TaskMeta`), ``prompt.md`` (templated, see ``prompts.py``) and
``grader.py`` (exports ``build_checks(f)``).
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from geocase.benchmark.taxonomy import TRAP_CATEGORIES_BY_DOMAIN, CheckKind


class CheckDecl(BaseModel):
    name: str
    kind: CheckKind


class TaskMeta(BaseModel):
    # A task.yaml key this model does not know about is a silent failure in
    # the benchmark's own tooling — pydantic's default would drop it (Plan 16).
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    name: str
    title: str
    function: str
    signature: str
    module: str
    handbook_id: str | None
    trap_category: str
    packages: list[str]
    origin: Literal["step0", "plan15", "plan16"]
    checks: list[CheckDecl]
    # Defaulted so the 20 geo task.yaml files stay untouched: they are not
    # hashed into run metadata, so leaving `geo` implicit costs no auditability.
    domain: str = "geo"

    @model_validator(mode="after")
    def _known_category(self) -> TaskMeta:
        # Cross-field: a category is valid only within its own domain, so a
        # geo task cannot declare a numeric trap and vice versa.
        try:
            allowed = TRAP_CATEGORIES_BY_DOMAIN[self.domain]
        except KeyError:
            raise ValueError(
                f"unknown domain {self.domain!r}; "
                f"known: {sorted(TRAP_CATEGORIES_BY_DOMAIN)}"
            ) from None
        if self.trap_category not in allowed:
            raise ValueError(
                f"unknown trap_category {self.trap_category!r} "
                f"for domain {self.domain!r}"
            )
        return self

    @property
    def directory(self) -> Path:
        return tasks_root() / self.name

    @property
    def prompt_template(self) -> str:
        return (self.directory / "prompt.md").read_text()

    @property
    def grader_path(self) -> Path:
        return self.directory / "grader.py"


def tasks_root() -> Path:
    return Path(__file__).parent / "tasks"


@cache
def _load_tasks() -> tuple[TaskMeta, ...]:
    tasks = []
    for yaml_path in sorted(tasks_root().glob("*/task.yaml")):
        meta = TaskMeta.model_validate(yaml.safe_load(yaml_path.read_text()))
        if meta.name != yaml_path.parent.name:
            raise ValueError(
                f"{yaml_path}: name {meta.name!r} != "
                f"directory {yaml_path.parent.name!r}"
            )
        tasks.append(meta)
    return tuple(tasks)


def all_tasks() -> list[TaskMeta]:
    return list(_load_tasks())


def get_task(name: str) -> TaskMeta:
    for task in _load_tasks():
        if task.name == name:
            return task
    raise KeyError(name)
