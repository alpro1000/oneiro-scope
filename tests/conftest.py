import importlib
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_pipeline_module() -> types.ModuleType:
    return importlib.import_module("etl.pipeline")


@pytest.fixture
def pipeline():
    return _load_pipeline_module()
