from api_probe.config.validator import ConfigValidator


def test_validator_detects_missing_probes():
    validator = ConfigValidator()
    is_valid, errors, warnings = validator.validate({})

    assert not is_valid
    assert "Missing required 'probes' field" in errors


def test_validator_valid_minimal_probe():
    cfg = {
        "probes": [
            {
                "name": "P1",
                "type": "rest",
                "endpoint": "https://example.com",
            }
        ]
    }

    validator = ConfigValidator()
    is_valid, errors, warnings = validator.validate(cfg)

    assert is_valid
    assert errors == []


def test_validator_rest_body_requires_content_type():
    cfg = {
        "probes": [
            {
                "name": "P1",
                "type": "rest",
                "endpoint": "https://example.com",
                "body": {"x": 1},
            }
        ]
    }

    validator = ConfigValidator()
    is_valid, errors, warnings = validator.validate(cfg)

    assert not is_valid
    assert any("Content-Type" in e for e in errors)


def test_validator_extract_variables_from_probes_and_executions():
    cfg = {
        "executions": [
            {
                "name": "CTX",
                "vars": [
                    {"BASE_URL": "${BASE_URL}"},
                    {"TOKEN": "static-token"},
                ],
            }
        ],
        "probes": [
            {
                "name": "P1",
                "type": "rest",
                "endpoint": "${BASE_URL}/health",
                "headers": {"Authorization": "Bearer ${TOKEN}"},
            }
        ],
    }

    validator = ConfigValidator()
    vars_found = validator.extract_variables(cfg)

    # Should include BASE_URL and TOKEN (from both executions and probes)
    assert "BASE_URL" in vars_found
    assert "TOKEN" in vars_found
