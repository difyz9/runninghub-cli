import json
from dataclasses import dataclass

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


@dataclass
class FakeWebhookDetail:
    task_id: str
    callback_status: str
    callback_response: str


class FakeDetailClient:
    def query_v2(self, task_id):
        return {
            "task_id": task_id,
            "status": "FAILED",
            "error_code": "805",
            "error_message": "工作流运行失败",
            "failed_reason": {"node_id": "99", "exception_message": "bad prompt"},
        }

    def get_status(self, task_id):
        return "FAILED"

    def get_outputs(self, task_id):
        return [{"node_id": "99", "file_url": "https://example.test/error.txt"}]

    def get_webhook_detail(self, task_id):
        return FakeWebhookDetail(
            task_id=task_id,
            callback_status="FAILED",
            callback_response="node 99 failed",
        )


class FakeTaskStatus:
    value = "QUEUED"


@dataclass
class FakeTask:
    task_id: str = "task-1"
    task_status: FakeTaskStatus = FakeTaskStatus()
    client_id: str = "client-1"
    prompt_tips: str = ""


class FakeSubmitClient:
    def __init__(self):
        self.ai_app_options = None
        self.workflow_options = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run_ai_app_with_modifier(self, webapp_id, modifier, **options):
        self.ai_app_options = options
        return FakeTask()

    def run_with_modifier(self, workflow_id, modifier, **options):
        self.workflow_options = options
        return FakeTask()


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


def test_task_detail_with_client_collects_failure_context():
    detail = service.task_detail_with_client(FakeDetailClient(), "task-1")

    assert detail["task_id"] == "task-1"
    assert detail["status"] == "FAILED"
    assert detail["error_code"] == "805"
    assert detail["failed_reason"] == {"node_id": "99", "exception_message": "bad prompt"}
    assert detail["query_v2"]["error_message"] == "工作流运行失败"
    assert detail["outputs"] == [{"node_id": "99", "file_url": "https://example.test/error.txt"}]
    assert detail["webhook_detail"]["callback_response"] == "node 99 failed"


def test_error_payload_includes_task_detail_attribute():
    exc = RuntimeError("failed")
    exc.task_detail = {"task_id": "task-1", "status": "FAILED"}

    payload = service.error_payload(exc)

    assert payload["task_detail"] == {"task_id": "task-1", "status": "FAILED"}


def test_submit_passes_access_password_to_webapp(monkeypatch):
    fake_client = FakeSubmitClient()
    monkeypatch.setattr(service, "create_client", lambda api_key=None, env_file=None: fake_client)

    result = service.submit(
        "2046575818536652802",
        "webapp",
        [],
        access_password="test-password",
    )

    assert fake_client.ai_app_options["access_password"] == "test-password"
    assert result["access_password_used"] is True


def test_submit_does_not_mark_access_password_for_workflow(monkeypatch):
    fake_client = FakeSubmitClient()
    monkeypatch.setattr(service, "create_client", lambda api_key=None, env_file=None: fake_client)

    result = service.submit("workflow-1", "workflow", [], access_password="ignored")

    assert "access_password" not in fake_client.workflow_options
    assert result["access_password_used"] is False
