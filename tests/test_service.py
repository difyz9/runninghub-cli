import json

from runninghub_cli import service


class FakeUploadedFile:
    file_name = "uploaded-video.mp4"
    download_url = "https://example.test/uploaded-video.mp4"


class FakeClient:
    def upload_image(self, path):
        return {
            "fileName": f"uploaded-{path.name}",
            "downloadUrl": f"https://example.test/uploaded-{path.name}",
        }

    def upload_file(self, path):
        return FakeUploadedFile()


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


def test_version_key_sorts_v_tags():
    assert service._version_key("v1.2.10") > service._version_key("v1.2.9")
    assert service._version_key("0.10.0") > service._version_key("0.9.9")


def test_upload_missing_file_raises(tmp_path):
    missing = tmp_path / "missing.png"
    try:
        service.upload(missing)
    except FileNotFoundError as exc:
        assert "文件不存在" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_process_upload_overrides_uses_file_name_for_upload_prefix(tmp_path):
    image = tmp_path / "input.png"
    image.write_bytes(b"png")

    overrides, uploads = service.process_upload_overrides(
        FakeClient(),
        [{"nodeId": "167", "fieldName": "image", "fieldValue": f"@upload:{image}"}],
    )

    assert overrides == [{"nodeId": "167", "fieldName": "image", "fieldValue": "uploaded-input.png"}]
    assert uploads[0]["kind"] == "image"
    assert uploads[0]["used"] == "fileName"


def test_process_upload_overrides_supports_upload_url_prefix(tmp_path):
    video = tmp_path / "input.mp4"
    video.write_bytes(b"mp4")

    overrides, uploads = service.process_upload_overrides(
        FakeClient(),
        [{"nodeId": "52", "fieldName": "video", "fieldValue": f"@upload-url:{video}"}],
    )

    assert overrides == [
        {"nodeId": "52", "fieldName": "video", "fieldValue": "https://example.test/uploaded-video.mp4"}
    ]
    assert uploads[0]["kind"] == "video"
    assert uploads[0]["used"] == "downloadUrl"


def test_infer_upload_kind_falls_back_to_suffix(tmp_path):
    audio = tmp_path / "voice.wav"
    assert service.infer_upload_kind({"fieldName": "source"}, audio) == "audio"
