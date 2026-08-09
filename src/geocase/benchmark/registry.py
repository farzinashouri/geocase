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
from pydantic import BaseModel, field_validator

from geocase.benchmark.taxonomy import TRAP_CATEGORIES, CheckKind


class CheckDecl(BaseModel):
    name: str
    kind: CheckKind


class TaskMeta(BaseModel):
    schema_version: Literal[1]
    name: str
    title: str
    function: str
    signature: str
    module: str
    handbook_id: str | None
    trap_category: str
    packages: list[str]
    origin: Literal["step0", "plan15"]
    checks: list[CheckDecl]

    @field_validator("trap_category")
    @classmethod
    def _known_category(cls, v: str) -> str:
        if v not in TRAP_CATEGORIES:
            raise ValueError(f"unknown trap_category {v!r}")
        return v

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
