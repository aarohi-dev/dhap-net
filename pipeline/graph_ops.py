# pipeline/graph_ops.py
# Re-exports from 05_graphframes_candidates.py with a valid Python module name.
# This allows test files to import graph functions without the numeric prefix issue.

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "_graphframes_candidates",
    Path(__file__).parent / "05_graphframes_candidates.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

k_hop_bfs = _mod.k_hop_bfs
build_adj  = _mod.build_adj
build_candidates_pandas = _mod.build_candidates_pandas
time_split = _mod.time_split

__all__ = ["k_hop_bfs", "build_adj", "build_candidates_pandas", "time_split"]
