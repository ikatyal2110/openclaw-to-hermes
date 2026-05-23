"""Extracts declared environment variables from openclaw.yaml and .env.example,
classifying each as 'secret' (needs secure handling on the Hermes side) or 'config'
based on common naming conventions."""

from __future__ import annotations

from pathlib import Path

from praxis_core.analyzers.base import Analyzer
from praxis_core.ir import IRGraph
from praxis_core.ir.models import Node, NodeKind, Provenance, make_node_id

# Tokens that, when they appear as a whole `_`-delimited segment of an env var
# name, indicate a credential. Matched case-insensitively.
_SECRET_TOKENS = frozenset(
    {
        "TOKEN",
        "KEY",
        "SECRET",
        "PASSWORD",
        "PASSWD",
        "CREDENTIAL",
        "CREDENTIALS",
        "PRIVATE",
        "AUTH",
        "BEARER",
        "SESSION",
        "COOKIE",
    }
)


def is_likely_secret(name: str) -> bool:
    """True if the env var name suggests it holds a credential.

    Matches whole underscore-delimited segments only, so `API_URL` does not match
    just because it contains `KEY`-adjacent text, but `OPENAI_API_KEY` does.
    Public so reports and tests can call the same heuristic.
    """
    return any(segment in _SECRET_TOKENS for segment in name.upper().split("_"))


class EnvAnalyzer(Analyzer):
    name = "openclaw.env"

    def analyze(self, root: Path) -> IRGraph:
        ir = IRGraph()
        seen: set[str] = set()

        manifest = self.safe_load_yaml(root / "openclaw.yaml")
        if isinstance(manifest, dict):
            for var in manifest.get("env", []) or []:
                if isinstance(var, str):
                    seen.add(var)

        env_file = root / ".env.example"
        if env_file.exists():
            for raw in env_file.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key = line.split("=", 1)[0].strip()
                if key:
                    seen.add(key)

        for var in sorted(seen):
            secret = is_likely_secret(var)
            ir.nodes.append(
                Node(
                    id=make_node_id("openclaw", NodeKind.ENV, var),
                    kind=NodeKind.ENV,
                    name=var,
                    provenance=Provenance(
                        framework="openclaw",
                        source_file=".env.example",
                        original_kind="env",
                    ),
                    metadata={
                        "secret": secret,
                        "classification": "secret" if secret else "config",
                    },
                )
            )

        return ir
