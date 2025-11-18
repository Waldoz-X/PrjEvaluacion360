#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para corregir errores de sintaxis en app.py"""

# Leer el archivo
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Corregir los errores
content = content.replace('porcentaje_breja', 'porcentaje_brecha')
content = content.replace('html.I className="fas fa-chart-pie me-2"', 'html.I(className="fas fa-chart-pie me-2"')

# Guardar el archivo corregido
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Errores de sintaxis corregidos:")
print("  - porcentaje_breja → porcentaje_brecha")
print("  - html.I className → html.I(className")

