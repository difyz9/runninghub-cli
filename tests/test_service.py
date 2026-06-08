import json

from runninghub_cli import service


def test_parse_overrides_inline_json():
    overrides = service.parse_overrides(
        '[{"nodeId":"43","fieldName":"text","fieldValue":"hello"}]'
    )
    assert overrides == [{"nodeId": "43", "fieldName": "text", "fieldValue": "hello"}]


def test_parse_overrides_wrapped_json(tmp_path):
    path = tmp_path / "overrides.json"
    path.write_text(
        json.dumps({"node_overrides": [{"node_id": "1", "field_name": "seed", "field_value": 7}]}),
        encoding="utf-8",
    )
    assert service.parse_overrides(path) == [{"node_id": "1", "field_name": "seed", "field_value": 7}]


def test_normalize_type():
    assert service.normalize_type("workflow") == "workflow"
    assert service.normalize_type("ai-app") == "webapp"
    assert service.normalize_type("ai_app") == "webapp"
    assert service.normalize_type("webapp") == "webapp"


def test_error_payload_shape():
    payload = service.error_payload(ValueError("bad input"))
    assert payload["ok"] is False
    assert payload["error_type"] == "ValueError"
    assert payload["error"] == "bad input"

