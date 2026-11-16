"""ローカルの .env と既存の環境変数による設定を確認する。"""

import runpy
import shutil
from pathlib import Path

import pytest


@pytest.fixture
def local_config(tmp_path, monkeypatch):
    for name in ("GEMINI_API_KEY", "AIE_MODEL", "AIE_RAG_DB"):
        # .env が追加する値も、テスト終了時に元の状態へ戻す。
        monkeypatch.setenv(name, "")
        monkeypatch.delenv(name, raising=False)
    # 実際の .env やキーを使わず、別のプロジェクトとして共通設定を読み込む。
    config_path = tmp_path / "app" / "config.py"
    config_path.parent.mkdir()
    shutil.copyfile(Path(__file__).resolve().parents[1] / "app" / "config.py", config_path)
    return tmp_path, config_path


def test_dotenv_loads_from_project_root(local_config, tmp_path, monkeypatch):
    root, config_path = local_config
    (root / ".env").write_text(
        'GEMINI_API_KEY="local-test-key"\nAIE_MODEL=local-test-model\n', encoding="utf-8-sig"
    )
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / ".env").write_text("GEMINI_API_KEY=wrong-project\n", encoding="utf-8")
    monkeypatch.chdir(elsewhere)

    config = runpy.run_path(str(config_path))

    assert config["get_api_key"]() == "local-test-key"
    assert config["MODEL"] == "local-test-model"


def test_existing_environment_takes_priority(local_config, monkeypatch):
    root, config_path = local_config
    (root / ".env").write_text(
        "GEMINI_API_KEY=local-test-key\nAIE_MODEL=local-test-model\n", encoding="utf-8"
    )
    monkeypatch.setenv("GEMINI_API_KEY", "environment-test-key")
    monkeypatch.setenv("AIE_MODEL", "environment-test-model")

    config = runpy.run_path(str(config_path))

    assert config["get_api_key"]() == "environment-test-key"
    assert config["MODEL"] == "environment-test-model"


def test_environment_works_without_dotenv(local_config, monkeypatch):
    _, config_path = local_config
    monkeypatch.setenv("GEMINI_API_KEY", "environment-test-key")

    config = runpy.run_path(str(config_path))

    assert config["get_api_key"]() == "environment-test-key"


def test_missing_key_explains_local_and_codespaces_setup(local_config):
    _, config_path = local_config
    config = runpy.run_path(str(config_path))

    with pytest.raises(SystemExit) as error:
        config["get_api_key"]()

    message = str(error.value)
    assert ".env" in message
    assert "$env:GEMINI_API_KEY" in message
    assert "Codespaces" in message
