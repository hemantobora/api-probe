"""YAML configuration loader with !include support."""

import os
from pathlib import Path
from typing import Any, Dict

import yaml


class IncludeLoader(yaml.SafeLoader):
    """Custom YAML loader supporting !include directive."""
    
    def __init__(self, stream):
        self._root = Path(stream.name).parent if hasattr(stream, 'name') else Path.cwd()
        super().__init__(stream)


def include_constructor(loader: IncludeLoader, node: yaml.Node) -> Any:
    """Handle !include directive."""
    path = loader.construct_scalar(node)
    
    # Resolve path relative to config file
    if not os.path.isabs(path):
        path = loader._root / path
    
    # Read and parse included file
    with open(path, 'r') as f:
        if path.suffix in ['.yaml', '.yml']:
            return yaml.load(f, IncludeLoader)
        elif path.suffix in ['.json']:
            import json
            return json.load(f)
        else:
            # Plain text (for .graphql files)
            return f.read()


# Register the !include constructor
IncludeLoader.add_constructor('!include', include_constructor)


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
        config = yaml.load(f, IncludeLoader)
    
    return config
