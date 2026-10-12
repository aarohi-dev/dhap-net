# pipeline/kafka_producer.py
# Alias for 03_kafka_producer.py (valid Python module name)
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "_kafka_producer",
    Path(__file__).parent / "03_kafka_producer.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

parse_line = _mod.parse_line
produce    = _mod.produce
get_producer = _mod.get_producer

__all__ = ["parse_line", "produce", "get_producer"]
