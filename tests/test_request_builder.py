from api_probe.http.builder import RequestBuilder


def test_build_rest_request_json_body():
    builder = RequestBuilder()

    req = builder.build_rest_request(
        endpoint="https://example.com",
        method="post",
        headers={"Content-Type": "application/json"},
        body={"a": 1},
    )

    assert req["method"] == "POST"
    assert req["url"] == "https://example.com"
    # Should be JSON-serialized
    assert req["data"] == '{"a": 1}'


def test_build_rest_request_form_body():
    builder = RequestBuilder()

    req = builder.build_rest_request(
        endpoint="https://example.com",
        method="post",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body={"a": "1", "b": "2"},
    )

    assert req["method"] == "POST"
    assert "a=1" in req["data"]
    assert "b=2" in req["data"]


def test_build_rest_request_missing_content_type_raises():
    builder = RequestBuilder()

    try:
        builder.build_rest_request(
            endpoint="https://example.com",
            method="post",
            headers={},
            body={"a": 1},
        )
        assert False, "Expected ValueError for missing Content-Type"
    except ValueError:
        pass


def test_build_graphql_request_sets_defaults():
    builder = RequestBuilder()

    req = builder.build_graphql_request(
        endpoint="https://example.com/graphql",
        query="query { ping }",
        variables={"id": 1},
        headers={},
    )

    assert req["method"] == "POST"
    assert req["url"] == "https://example.com/graphql"
    # Content-Type should be enforced
    assert any(k.lower() == "content-type" for k in req["headers"].keys())
    assert "query" in req["data"]
    assert "variables" in req["data"]