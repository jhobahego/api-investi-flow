"""
Configuración inicial de la aplicación.
Este módulo se ejecuta antes que cualquier otro import.
"""

import warnings

# Suprimir warnings de Pydantic antes de que cualquier módulo los genere
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
