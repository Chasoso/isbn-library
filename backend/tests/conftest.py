from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


TESTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TESTS_DIR.parent
LAMBDA_DIR = BACKEND_DIR / "lambda"
SHARED_DIR = LAMBDA_DIR / "shared" / "python"

if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))


def load_handler_module(handler_dir_name: str) -> ModuleType:
    module_path = LAMBDA_DIR / handler_dir_name / "handler.py"
    module_name = f"tests_{handler_dir_name}_handler"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def lambda_event() -> dict[str, Any]:
    return {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                    }
                }
            }
        }
    }


def parse_response(response: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    return response["statusCode"], json.loads(response["body"] or "{}")
