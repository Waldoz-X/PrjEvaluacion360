import pandas as pd
import numpy as np

# Mock data
data = {
    'Evaluado': ['A', 'A', 'B', 'B'],
    'Comp1': [4, 5, 3, 4],
    'Comp2': [3, 4, 2, 3]
}
df = pd.DataFrame(data)
COL_EVALUADO = 'Evaluado'
comps_cat = ['Comp1', 'Comp2']

# Current logic
try:
    prom = df.groupby(COL_EVALUADO)[comps_cat].mean().mean()
    print(f"Current logic result type: {type(prom)}")
    print(f"Current logic result: {prom}")
except Exception as e:
    print(f"Current logic error: {e}")

# Proposed fix 1: Average of averages per evaluado
prom_fix1 = df.groupby(COL_EVALUADO)[comps_cat].mean().mean(axis=1).mean()
print(f"Fix 1 (Avg of Avgs per Evaluado) result: {prom_fix1}")

# Proposed fix 2: Global average of all responses
prom_fix2 = df[comps_cat].mean().mean()
print(f"Fix 2 (Global Avg) result: {prom_fix2}")
