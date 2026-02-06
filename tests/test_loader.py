import os
from pathlib import Path

from api_probe.config.loader import load_config


def test_load_simple_yaml(tmp_path: Path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("probes:\n  - name: 'Test'\n")

    config = load_config(str(cfg_path))

    assert "probes" in config
    assert config["probes"][0]["name"] == "Test"


def test_include_json(tmp_path: Path):
    json_path = tmp_path / "body.json"
    json_path.write_text('{"key": "value"}')

    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("body: !include body.json\n")

    config = load_config(str(cfg_path))

    assert config["body"] == {"key": "value"}


def test_include_graphql(tmp_path: Path):
    gql_path = tmp_path / "query.graphql"
    gql_path.write_text("query { ping }\n")

    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("query: !include query.graphql\n")

    config = load_config(str(cfg_path))

    assert config["query"] == "query { ping }\n"