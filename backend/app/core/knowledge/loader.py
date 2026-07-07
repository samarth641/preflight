"""YAML rule loader for the knowledge base."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.core.knowledge.models import KnowledgeBase, Rule

logger = logging.getLogger(__name__)

DEFAULT_KNOWLEDGE_DIRS = ("pytorch", "rocm", "cuda", "huggingface", "deepspeed", "datasets", "hardware")


class RuleLoader:
    """Automatically discovers and loads YAML rule files from the knowledge directory."""

    def __init__(self, knowledge_root: Path | str | None = None) -> None:
        self.knowledge_root = self._resolve_knowledge_root(knowledge_root)

    @staticmethod
    def _resolve_knowledge_root(knowledge_root: Path | str | None) -> Path:
        if knowledge_root is not None:
            return Path(knowledge_root).resolve()

        # backend/app/core/knowledge -> project root/knowledge
        backend_root = Path(__file__).resolve().parents[3]
        project_root = backend_root.parent
        return project_root / "knowledge"

    def load(self) -> KnowledgeBase:
        """Load all YAML rules from the knowledge directory tree."""
        rules: list[Rule] = []
        sources: set[str] = set()
        categories: set[str] = set()
        load_errors: list[str] = []

        if not self.knowledge_root.exists():
            message = f"Knowledge directory not found: {self.knowledge_root}"
            logger.warning(message)
            return KnowledgeBase(load_errors=[message])

        yaml_files = sorted(self.knowledge_root.rglob("*.yaml")) + sorted(
            self.knowledge_root.rglob("*.yml")
        )

        for yaml_path in yaml_files:
            file_rules, file_errors = self._load_file(yaml_path)
            rules.extend(file_rules)
            load_errors.extend(file_errors)

            for rule in file_rules:
                sources.add(rule.source)
                categories.add(rule.category)

        unique_rules = self._deduplicate_rules(rules)
        if len(unique_rules) < len(rules):
            logger.warning(
                "Removed %d duplicate rule(s) by id",
                len(rules) - len(unique_rules),
            )

        logger.info(
            "Loaded %d rules from %d file(s) in %s",
            len(unique_rules),
            len(yaml_files),
            self.knowledge_root,
        )

        return KnowledgeBase(
            rules=unique_rules,
            sources=sorted(sources),
            categories=sorted(categories),
            load_errors=load_errors,
        )

    def _load_file(self, yaml_path: Path) -> tuple[list[Rule], list[str]]:
        rules: list[Rule] = []
        errors: list[str] = []

        try:
            raw_content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            message = f"Failed to read {yaml_path}: {exc}"
            logger.error(message)
            return [], [message]

        if raw_content is None:
            return [], []

        rule_payloads = self._extract_rule_payloads(raw_content)

        for index, payload in enumerate(rule_payloads):
            try:
                rules.append(Rule.model_validate(payload))
            except ValidationError as exc:
                message = f"Validation error in {yaml_path} (entry {index}): {exc}"
                logger.error(message)
                errors.append(message)

        return rules, errors

    @staticmethod
    def _extract_rule_payloads(raw_content: Any) -> list[dict[str, Any]]:
        if isinstance(raw_content, list):
            return [item for item in raw_content if isinstance(item, dict)]

        if isinstance(raw_content, dict):
            if "rules" in raw_content and isinstance(raw_content["rules"], list):
                return [item for item in raw_content["rules"] if isinstance(item, dict)]
            return [raw_content]

        return []

    @staticmethod
    def _deduplicate_rules(rules: list[Rule]) -> list[Rule]:
        seen: set[str] = set()
        unique: list[Rule] = []

        for rule in sorted(rules, key=lambda r: (-r.priority, -r.confidence)):
            if rule.id in seen:
                continue
            seen.add(rule.id)
            unique.append(rule)

        return unique

    def ensure_structure(self) -> None:
        """Create expected knowledge subdirectories if they do not exist."""
        self.knowledge_root.mkdir(parents=True, exist_ok=True)
        for directory in DEFAULT_KNOWLEDGE_DIRS:
            (self.knowledge_root / directory).mkdir(parents=True, exist_ok=True)
