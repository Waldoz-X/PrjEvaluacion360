import utils_reporte
import io

# Mock data
datos = {
    'meta': {
        'evaluado': 'Test User',
        'total_evaluadores': 5,
        'conteo_evaluadores': {'Jefe': 1, 'Colegas': 2, 'Subordinados': 2}
    },
    'kpis': {
        'calificacion_final': 4.2,
        'nivel_cumplimiento': 95,
        'consistencia': 4.5,
        'percentil': 10,
        'brecha_mejora': 0.8
    },
    'textos': {
        'estado_aptitud': 'ALTO DESEMPEÑO',
        'mensaje_aptitud': 'Buen trabajo',
        'recomendacion_rh': 'Promover',
        'cuadrante': 'ESTRELLA',
        'descripcion_cuadrante': 'Talento clave',
        'accion_rh': 'Retener',
        'fortalezas': [('Liderazgo', 4.5), ('Comunicación', 4.4)],
        'mejoras': [('Gestión', 3.8)]
    },
    'data_raw': {
        'promedios_categorias': {
            'Liderazgo': 4.5,
            'Comunicación': 4.4,
            'Gestión': 3.8,
            'Innovación': 4.0
        },
        'colores_categorias': {
            'Liderazgo': '#FF0000',
            'Comunicación': '#00FF00',
            'Gestión': '#0000FF',
            'Innovación': '#FFFF00'
        },
        'promedios_empresa_cat': [4.0, 4.0, 3.5, 3.8],
        'promedios_por_grupo': {
            'Autoevaluación': [4.5, 4.4, 3.8, 4.0],
            'Jefe Inmediato': [4.0, 4.2, 3.5, 3.9],
            'Colegas': [4.2, 4.3, 3.7, 4.1],
            'Subordinados': [4.6, 4.5, 4.0, 4.2]
        }
    }
}

print("Testing PDF generation...")
try:
    pdf = utils_reporte.generar_pdf(datos)
    if pdf:
        print(f"PDF generated successfully ({len(pdf.getvalue())} bytes)")
    else:
        print("PDF generation failed (returned None)")
except Exception as e:
    print(f"PDF generation error: {e}")
    import traceback
    traceback.print_exc()

print("\nTesting Word generation...")
try:
    word = utils_reporte.generar_word(datos)
    if word:
        print(f"Word generated successfully ({len(word.getvalue())} bytes)")
    else:
        print("Word generation failed (returned None)")
except Exception as e:
    print(f"Word generation error: {e}")
    import traceback
    traceback.print_exc()
