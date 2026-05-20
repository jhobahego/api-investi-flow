# Instrucciones para Agentes de IA (investi-flow-api)

Este archivo contiene reglas y directrices esenciales para cualquier agente de IA que trabaje en este repositorio.

## Activación del Entorno Virtual

> [!IMPORTANT]
> Siempre se debe activar el entorno virtual de Python antes de ejecutar pruebas, formateadores, linters o realizar confirmaciones (commits) de Git.

### Comando para Activar el Entorno

Desde el directorio del backend (`investi-flow-api` o la raíz si corresponde), asegúrate de ejecutar:

```bash
source .venv/bin/activate
```

### Flujo de Trabajo Requerido para Commits y Pruebas

1. **Activar el entorno virtual**: `source .venv/bin/activate`
2. **Ejecutar herramientas de calidad**: El proyecto cuenta con un comando muy completo en el `Makefile` para formatear, verificar tests y lintar todo el proyecto:

   ```bash
   make quality
   ```

   *Nota: Siempre ejecuta este comando antes de confirmar (commit) o subir cambios para garantizar que todo el código esté limpio y las pruebas pasen.*
3. **Realizar el commit** de forma granular con el entorno virtual activo (para asegurar que los hooks de pre-commit se ejecuten correctamente con las dependencias instaladas en el entorno virtual). Usa el comando `git log` para ver el formato de los mensajes; verifica el formato, el idioma y la longitud del commit, y aplica esas practicas al redactar y crear el commit con `git commit -m "mensaje-con-estas-pautas"`.
