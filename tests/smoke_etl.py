"""Quick smoke-test for ETL parsing."""
import sys
sys.path.insert(0, 'e:/GitHub/dhap-net')

# Can't import 02_etl_flows directly due to numeric module name
# so import the functions manually
import importlib.util
spec = importlib.util.spec_from_file_location(
    "etl_flows",
    "e:/GitHub/dhap-net/pipeline/02_etl_flows.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

lines = []
with open('e:/GitHub/dhap-net/reports/data/flows.txt', 'r',
          encoding='utf-8', errors='replace') as f:
    for i, l in enumerate(f):
        lines.append(l)
        if i >= 49999:
            break

df, bad = mod.parse_chunk(lines)
print(f'Parsed: {len(df)} rows, {bad} bad')
agg = mod.aggregate(df)
print(f'Aggregated: {len(agg)} rows')
print(f'dtypes:\n{agg.dtypes}')

import pyarrow as pa
import pyarrow.parquet as pq
tbl = pa.Table.from_pandas(agg, preserve_index=False)
print(f'PyArrow schema: {tbl.schema}')
print('Smoke test PASSED')
