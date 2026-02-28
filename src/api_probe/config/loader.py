"""YAML configuration loader with !include and type-coercion tag support."""

import os
import sys
from pathlib import Path
from typing import Any, Dict

import yaml


# ---------------------------------------------------------------------------
# Typed value marker
# ---------------------------------------------------------------------------

class TypedValue:
    """Wraps a raw YAML scalar with an explicit target type.

    Created by !int, !bool, !float, !str tags in YAML.
    The substitution engine resolves the inner string first, then coerces.

    Example:
        !int "${PAGE_SIZE}"   → TypedValue(int, "${PAGE_SIZE}")
        !bool "${IS_ACTIVE}"  → TypedValue(bool, "${IS_ACTIVE}")
    """

    _COERCIONS = {
        'int':   int,
        'float': float,
        'str':   str,
        'bool':  None,  # handled specially — see coerce()
    }

    def __init__(self, target_type: str, raw: str):
        self.target_type = target_type  # 'int' | 'float' | 'str' | 'bool'
        self.raw = raw

    def coerce(self, substituted: str) -> Any:
        """Attempt to coerce substituted string to target type.

        Args:
            substituted: String after variable substitution

        Returns:
            Coerced value, or the original string if coercion fails
        """
        if self.target_type == 'bool':
            lower = substituted.strip().lower()
            if lower in ('true', '1', 'yes'):
                return True
            if lower in ('false', '0', 'no'):
                return False
            # Coercion failed — warn and fall back
            print(
                f"[WARN] !bool coercion failed for value '{substituted}' "
                f"(expected true/false/yes/no/1/0) — keeping as string",
                file=sys.stderr,
            )
            return substituted

        converter = self._COERCIONS.get(self.target_type, str)
        try:
            return converter(substituted)
        except (ValueError, TypeError):
            print(
                f"[WARN] !{self.target_type} coercion failed for value '{substituted}' "
                f"— keeping as string",
                file=sys.stderr,
            )
            return substituted

    def __repr__(self):
        return f"TypedValue({self.target_type!r}, {self.raw!r})"


# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------

class IncludeLoader(yaml.SafeLoader):
    """Custom YAML loader supporting !include and type-coercion directives."""

    def __init__(self, stream):
        self._root = Path(stream.name).parent if hasattr(stream, 'name') else Path.cwd()
        super().__init__(stream)


def include_constructor(loader: IncludeLoader, node: yaml.Node) -> Any:
    """Handle !include directive."""
    path = loader.construct_scalar(node)

    if not os.path.isabs(path):
        path = loader._root / path

    with open(path, 'r') as f:
        if Path(path).suffix in ('.yaml', '.yml'):
            return yaml.load(f, IncludeLoader)
        elif Path(path).suffix == '.json':
            import json
            return json.load(f)
        else:
            return f.read()


def _make_type_constructor(target_type: str):
    """Return a YAML constructor that wraps the scalar in a TypedValue."""
    def constructor(loader: IncludeLoader, node: yaml.Node) -> TypedValue:
        raw = loader.construct_scalar(node)
        return TypedValue(target_type, raw)
    return constructor


# Register constructors
IncludeLoader.add_constructor('!include', include_constructor)
IncludeLoader.add_constructor('!int',   _make_type_constructor('int'))
IncludeLoader.add_constructor('!float', _make_type_constructor('float'))
IncludeLoader.add_constructor('!bool',  _make_type_constructor('bool'))
IncludeLoader.add_constructor('!str',   _make_type_constructor('str'))


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Parsed configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is invalid
    """
    with open(config_path, 'r') as f:
        return yaml.load(f, IncludeLoader)
