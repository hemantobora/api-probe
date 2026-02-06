import pytest

from api_probe.config.parser import ConfigParser
from api_probe.config.models import Probe, Group, Execution, Validation


def test_parse_minimal_probe():
    parser = ConfigParser()
    config_dict = {
        "probes": [
            {
                "name": "Test",
                "type": "rest",
                "endpoint": "https://example.com",
            }
        ]
    }

    config = parser.parse(config_dict)

    assert len(config.probes) == 1
    probe = config.probes[0]
    assert isinstance(probe, Probe)
    assert probe.name == "Test"
    assert probe.type == "rest"
    assert probe.endpoint == "https://example.com"
    assert probe.method == "GET"  # default


def test_parse_rest_with_body_requires_content_type():
    parser = ConfigParser()
    config_dict = {
        "probes": [
            {
                "name": "Test",
                "type": "rest",
                "endpoint": "https://example.com",
                "body": {"a": 1},
            }
        ]
    }

    with pytest.raises(ValueError):
        parser.parse(config_dict)


def test_parse_graphql_requires_query():
    parser = ConfigParser()
    config_dict = {
        "probes": [
            {
                "name": "GQL",
                "type": "graphql",
                "endpoint": "https://example.com/graphql",
            }
        ]
    }

    with pytest.raises(ValueError):
        parser.parse(config_dict)


def test_parse_group_generates_name(monkeypatch):
    from api_probe.execution import name_generator

    # Ensure deterministic name
    monkeypatch.setattr(name_generator, "generate_name", lambda: "generated-name")

    parser = ConfigParser()
    config_dict = {
        "probes": [
            {
                "group": {
                    "probes": [
                        {
                            "name": "P1",
                            "type": "rest",
                            "endpoint": "https://example.com",
                        }
                    ]
                }
            }
        ]
    }

    config = parser.parse(config_dict)
    assert len(config.probes) == 1
    group = config.probes[0]
    assert isinstance(group, Group)
    assert group.name == "generated-name"
    assert len(group.probes) == 1


def test_parse_executions_block():
    parser = ConfigParser()
    config_dict = {
        "executions": [
            {
                "name": "CTX",
                "vars": [{"FOO": "bar"}],
                "validations": {"Probe": {"status": 201}},
            }
        ],
        "probes": [
            {
                "name": "P1",
                "type": "rest",
                "endpoint": "https://example.com",
            }
        ],
    }

    config = parser.parse(config_dict)

    assert len(config.executions) == 1
    execution = config.executions[0]
    assert isinstance(execution, Execution)
    assert execution.name == "CTX"
    assert execution.vars == [{"FOO": "bar"}]
    assert execution.validations["Probe"]["status"] == 201


def test_parse_validation_block():
    parser = ConfigParser()
    config_dict = {
        "probes": [
            {
                "name": "P1",
                "type": "rest",
                "endpoint": "https://example.com",
                "validation": {
                    "status": 200,
                    "response_time": 1000,
                    "headers": {"present": ["X-Test"]},
                    "body": {"present": ["id"]},
                },
            }
        ]
    }

    config = parser.parse(config_dict)

    probe = config.probes[0]
    assert isinstance(probe.validation, Validation)
    assert probe.validation.status == 200
    assert probe.validation.response_time == 1000
    assert probe.validation.headers == {"present": ["X-Test"]}
    assert probe.validation.body == {"present": ["id"]}
