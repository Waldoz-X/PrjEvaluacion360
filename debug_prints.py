from app import COL_EVALUADO, COL_RELACION, comp_cols, evaluados_options
print('COL_EVALUADO =', COL_EVALUADO)
print('COL_RELACION =', COL_RELACION)
print('N_competencias =', len(comp_cols))
print('First 10 competencias:')
for c in comp_cols[:10]:
    print(' -', c)
print('First 10 evaluados:')
for o in evaluados_options[:10]:
    print(' -', o['value'])
