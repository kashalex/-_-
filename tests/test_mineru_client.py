from pathlib import Path

from estimate_extractor.mineru_client import MinerUClient


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def test_agent_mode_uses_signed_upload_flow(monkeypatch, tmp_path):
    source = tmp_path / "09-07.xlsx"
    source.write_bytes(b"fake xlsx")
    calls = []

    def fake_post(url, json=None, timeout=None, **kwargs):
        calls.append(("post", url, json, kwargs))
        assert "files" not in kwargs
        assert json["file_name"] == source.name
        return FakeResponse(payload={"code": 0, "data": {"task_id": "task-1", "file_url": "https://upload.example/file"}})

    def fake_put(url, data=None, timeout=None, **kwargs):
        calls.append(("put", url, data.read(), kwargs))
        return FakeResponse(status_code=200)

    def fake_get(url, timeout=None, **kwargs):
        calls.append(("get", url, None, kwargs))
        if url.endswith("/api/v1/agent/parse/task-1"):
            return FakeResponse(payload={"code": 0, "data": {"state": "done", "markdown_url": "https://cdn.example/full.md"}})
        return FakeResponse(text="| № | Код | Наименование | Ед. | Количество |")

    monkeypatch.setattr("estimate_extractor.mineru_client.requests.post", fake_post)
    monkeypatch.setattr("estimate_extractor.mineru_client.requests.put", fake_put)
    monkeypatch.setattr("estimate_extractor.mineru_client.requests.get", fake_get)

    markdown = MinerUClient(poll_interval=0).convert_file(str(source), mode="agent", language="ru")

    assert markdown.startswith("| № | Код")
    assert [call[0] for call in calls] == ["post", "put", "get", "get"]
