"""MinerU API client with accurate and lightweight agent conversion modes."""

from __future__ import annotations

import io
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests


class MinerUError(RuntimeError):
    """Raised when MinerU conversion fails."""


@dataclass
class MinerUClient:
    api_key: Optional[str] = None
    base_url: str = "https://mineru.net"
    timeout: int = 60
    poll_interval: int = 3
    max_wait_seconds: int = 600

    def convert_file(self, file_path: str, mode: str = "accurate", model_version: str = "vlm", language: str = "ru") -> str:
        """Convert a local file to Markdown via MinerU, never parsing source files directly."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        if mode == "accurate":
            return self._convert_accurate_upload(path, model_version=model_version, language=language)
        if mode == "agent":
            return self._convert_agent_file(path)
        raise ValueError("mode должен быть 'accurate' или 'agent'")

    def _convert_accurate_upload(self, path: Path, model_version: str, language: str) -> str:
        if not self.api_key:
            raise MinerUError("Для режима accurate нужен MINERU_API_KEY или ключ в интерфейсе")
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        payload = {
            "files": [{"name": path.name, "data_id": path.stem}],
            "model_version": model_version,
            "language": language,
            "enable_table": True,
            "enable_formula": True,
        }
        response = requests.post(f"{self.base_url}/api/v4/file-urls/batch", headers=headers, json=payload, timeout=self.timeout)
        data = self._json(response)
        if data.get("code") != 0:
            raise MinerUError(data.get("msg", "Не удалось получить ссылку загрузки MinerU"))
        upload_url = data["data"]["file_urls"][0]
        batch_id = data["data"]["batch_id"]
        with path.open("rb") as source:
            upload_response = requests.put(upload_url, data=source, timeout=self.timeout)
        if upload_response.status_code >= 400:
            raise MinerUError(f"Ошибка загрузки файла в MinerU: HTTP {upload_response.status_code}")
        zip_url = self._poll_batch(batch_id, headers)
        return self._download_markdown_from_zip(zip_url)

    def _convert_agent_file(self, path: Path) -> str:
        with path.open("rb") as source:
            files = {"file": (path.name, source)}
            response = requests.post(f"{self.base_url}/api/v1/agent/parse/file", files=files, timeout=self.timeout)
        data = self._json(response)
        if data.get("code") != 0:
            raise MinerUError(data.get("msg", "Не удалось создать agent-задачу MinerU"))
        task_id = data.get("data", {}).get("task_id") or data.get("data", {}).get("id")
        if not task_id:
            markdown_url = data.get("data", {}).get("markdown_url") or data.get("data", {}).get("md_url")
            if markdown_url:
                return requests.get(markdown_url, timeout=self.timeout).text
            raise MinerUError("MinerU Agent не вернул task_id или markdown_url")
        markdown_url = self._poll_agent(task_id)
        return requests.get(markdown_url, timeout=self.timeout).text

    def _poll_batch(self, batch_id: str, headers: dict) -> str:
        deadline = time.time() + self.max_wait_seconds
        last_state = "unknown"
        while time.time() < deadline:
            response = requests.get(f"{self.base_url}/api/v4/extract-results/batch/{batch_id}", headers=headers, timeout=self.timeout)
            data = self._json(response)
            if data.get("code") != 0:
                raise MinerUError(data.get("msg", "Ошибка запроса batch-результата MinerU"))
            extracts = data.get("data", {}).get("extract_result") or data.get("data", {}).get("extract_results") or []
            if extracts:
                result = extracts[0]
                last_state = result.get("state", last_state)
                if last_state == "done" and result.get("full_zip_url"):
                    return result["full_zip_url"]
                if last_state == "failed":
                    raise MinerUError(result.get("err_msg", "MinerU не смог обработать документ"))
            time.sleep(self.poll_interval)
        raise MinerUError(f"Превышено время ожидания MinerU, последний статус: {last_state}")

    def _poll_agent(self, task_id: str) -> str:
        deadline = time.time() + self.max_wait_seconds
        last_state = "unknown"
        while time.time() < deadline:
            response = requests.get(f"{self.base_url}/api/v1/agent/parse/result/{task_id}", timeout=self.timeout)
            data = self._json(response)
            if data.get("code") != 0:
                raise MinerUError(data.get("msg", "Ошибка запроса agent-результата MinerU"))
            payload = data.get("data", {})
            last_state = payload.get("state", payload.get("status", last_state))
            markdown_url = payload.get("markdown_url") or payload.get("md_url") or payload.get("url")
            if last_state in {"done", "success", "completed"} and markdown_url:
                return markdown_url
            if last_state == "failed":
                raise MinerUError(payload.get("err_msg", "MinerU Agent не смог обработать документ"))
            time.sleep(self.poll_interval)
        raise MinerUError(f"Превышено время ожидания MinerU Agent, последний статус: {last_state}")

    def _download_markdown_from_zip(self, zip_url: str) -> str:
        response = requests.get(zip_url, timeout=self.timeout)
        if response.status_code >= 400:
            raise MinerUError(f"Не удалось скачать ZIP MinerU: HTTP {response.status_code}")
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            candidates = [name for name in archive.namelist() if name.endswith("full.md")]
            if not candidates:
                candidates = [name for name in archive.namelist() if name.lower().endswith(".md")]
            if not candidates:
                raise MinerUError("В ZIP MinerU не найден Markdown-файл")
            with archive.open(candidates[0]) as md_file:
                return md_file.read().decode("utf-8")

    @staticmethod
    def _json(response: requests.Response) -> dict:
        if response.status_code >= 400:
            raise MinerUError(f"MinerU HTTP {response.status_code}: {response.text[:300]}")
        try:
            return response.json()
        except ValueError as exc:
            raise MinerUError("MinerU вернул не JSON-ответ") from exc
