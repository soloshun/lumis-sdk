"""Small reference-agent configuration; no enterprise reasoning or production policy engine."""

from pathlib import PurePosixPath
from typing import Self

from pydantic import Field, model_validator

from lumis_sdk.core.contracts import Contract, Identifier, Text
from lumis_sdk.investigation.contracts import AgentBudget
from lumis_sdk.sandbox import SandboxPolicy


def approved_file(path: str) -> str:
    parsed = PurePosixPath(path)
    denied_parts = {".git", ".env", "secrets", "node_modules", ".venv", "__pycache__"}
    if (
        parsed.is_absolute()
        or ".." in parsed.parts
        or not parsed.parts
        or any(part.lower() in denied_parts or part.startswith(".") for part in parsed.parts)
        or parsed.suffix.lower()
        not in {".py", ".sql", ".toml", ".yaml", ".yml", ".json", ".txt", ".md"}
        or str(parsed) != path
        or path.startswith("-")
        or "\\" in path
    ):
        raise ValueError("code inspection requires explicit relative non-secret text file paths")
    return path


class CodeRepository(Contract):
    id: Identifier
    root: Text
    entity_ids: tuple[Identifier, ...] = Field(min_length=1, max_length=100)
    files: tuple[Identifier, ...] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_files(self) -> Self:
        if len(set(self.files)) != len(self.files):
            raise ValueError("duplicate code file paths")
        for path in self.files:
            approved_file(path)
        return self


class InvestigatorSettings(Contract):
    budget: AgentBudget = Field(default_factory=AgentBudget)
    repositories: tuple[CodeRepository, ...] = Field(default=(), max_length=10)
    sandbox: SandboxPolicy = Field(default_factory=SandboxPolicy)

    @model_validator(mode="after")
    def unique_repositories(self) -> Self:
        if len({repo.id for repo in self.repositories}) != len(self.repositories):
            raise ValueError("duplicate repository IDs")
        return self
