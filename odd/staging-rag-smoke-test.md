# Staging RAG smoke test — real worker

Objetivo: subir `Planteamiento del problema.docx` a la API de staging, indexarlo con un
worker Celery real (local), verificar los chunks en pgvector y probar los endpoints de IA
con contexto RAG.

## Datos preparados

| Dato | Valor |
|------|-------|
| Documento | `Planteamiento del problema.docx` (7.684 bytes, 5 párrafos, 3.818 caracteres, 0 tablas) |
| Usuario | `staging.rag.smoke@example.com` |
| Password | `RagSmoke123` (cumple mayúscula, minúscula y número) |
| Teléfono | `+573001112233` |
| Nombre | `Staging RAG Smoke` |
| Proyecto | `RAG Staging Smoke <timestamp>` |
| Tipo de investigación | `experimental` |
| Institución | `Staging` |
| Estado | `in_progress` |
| Consulta de búsqueda | `¿Cuál es el planteamiento del problema y cuáles son sus causas principales?` |
| Pregunta de chat | `Resume el planteamiento del problema del documento y menciona las causas principales.` |

El script crea el usuario (o hace login si ya existe), crea el proyecto, sube el DOCX,
espera a que el worker indexe, consulta `/documentos/{id}/search`, llama al chat y a
sugerencias. No imprime tokens ni passwords.

## Prerrequisitos

1. La API de staging debe correr la rama `feat/rag-documents-backend` (o levantar la API
   localmente contra el Neon de staging). Las variables de entorno solas no activan el
   código nuevo.
2. La base de staging debe estar migrada a `f3a9c1d7b2e4` (ya aplicado en Neon).
3. Upstash configurado en la API con las mismas `CELERY_BROKER_URL` y
   `CELERY_RESULT_BACKEND` que usará el worker local.
4. El worker local debe poder salir a Neon, Upstash y Google.

## 1. Configurar el worker local

```bash
cp .env.staging-worker.example .env.staging-worker
# Editar .env.staging-worker con los valores reales de Neon, Upstash y Google.
```

El archivo `.env.staging-worker` está gitignored. No commitear secretos.

## 2. Arrancar el worker

```bash
make staging-worker
```

Equivale a:

```bash
.venv/bin/dotenv -f .env.staging-worker run -- \
  .venv/bin/celery -A app.core.celery_app.celery_app worker \
  --loglevel=info --concurrency=1 -Q rag
```

No uses `set -a; source .env.staging-worker` si `DATABASE_URL` tiene `&` sin comillas: el shell corta la URL y el worker arranca con la DB local (índice en 0). El archivo de ejemplo ya trae las URLs entre comillas, y `make staging-worker` usa `dotenv` para evitar ese problema.

Dejar la terminal abierta. Mientras el worker esté apagado, los tasks quedan encolados en
Upstash y se procesan al arrancar.

## 3. Verificar la API de staging

En Render, la API de staging debe tener:

```env
CELERY_BROKER_URL=rediss://default:<password>@<endpoint>:6379/0
CELERY_RESULT_BACKEND=rediss://default:<password>@<endpoint>:6379/0
RATE_LIMIT_REDIS_URL=async+rediss://default:<password>@<endpoint>:6379
RAG_INDEXING_ENABLED=true
AI_MODEL_EMBEDDING=gemini-embedding-001
```

La misma base de Upstash se comparte entre el cost guard y Celery; las claves no colisionan,
pero la cuota de comandos es compartida.

## 4. Ejecutar el smoke test

Contra staging:

```bash
API_BASE_URL=https://<staging>.onrender.com \
  .venv/bin/python scripts/staging_rag_smoke_test.py
```

Contra una API local (misma base de staging y mismo Upstash):

```bash
API_BASE_URL=http://127.0.0.1:8000 \
  .venv/bin/python scripts/staging_rag_smoke_test.py
```

Para borrar el proyecto al final:

```bash
API_BASE_URL=https://<staging>.onrender.com CLEANUP=1 \
  .venv/bin/python scripts/staging_rag_smoke_test.py
```

## 5. Resultado esperado

1. `health: 200 ...`
2. `register: OK` o `register: el usuario ya existe, se intenta login`
3. `login: OK`
4. `project_id: <id>`
5. `attachment_id: <id> file: Planteamiento del problema.docx`
6. `search: N resultados` con líneas:
   `- Planteamiento del problema.docx chunk=0 sim=0.7xx :: ...`
7. `chat: model=gemini-... conversation_id=<id>` y una respuesta que menciona el
   planteamiento del problema.
8. `suggestion: model=gemini-...` y una continuación académica.
9. `SMOKE TEST OK`

Resultado observado en la prueba local (API local + worker contra Upstash, DB local) y en la prueba real de staging:

- 5 chunks para el DOCX, similitudes `0.655`, `0.629`, `0.602`, `0.600`, `0.589`.
- Chat `gemini-2.5-flash-lite` respondiendo con el resumen del planteamiento y citando
  `Planteamiento del problema.docx`.
- Sugerencia `gemini-2.5-flash-lite` continuando el texto académico.
- `CLEANUP=1` archiva el proyecto y luego lo elimina definitivamente.

## Troubleshooting

| Síntoma | Causa probable | Acción |
|---------|----------------|--------|
| `No se pudo conectar a la API` | URL incorrecta o API dormida | Revisar `API_BASE_URL`; despertar el servicio |
| `register falló` 400 | Password débil o email inválido | Usar `RagSmoke123` y un email válido |
| `login falló` 401 | Usuario existe con otra password | Cambiar `TEST_EMAIL` o `TEST_PASSWORD` |
| `search 404` | API sin la rama RAG | Redeployar staging con `feat/rag-documents-backend` |
| `Sin chunks después de 90s` | Worker apagado, broker distinto o `RAG_INDEXING_ENABLED=false` | Revisar logs del worker y que las `CELERY_*` de la API y el worker sean iguales |
| Worker procesa pero `0 fragmentos` | `DATABASE_URL` no exportada (URL con `&` sin comillas) o DB local | Usar `make staging-worker`; confirmar que el worker use Neon y no `localhost` |
| `SSL connection has been closed unexpectedly` al registrar | Conexión idle de Neon/pgbouncer | Redesplegar la API con `pool_pre_ping=True`; reintentar el smoke test |
| `A rediss:// URL must have parameter ssl_cert_reqs` | Celery no tiene política TLS | Actualizar `app/core/celery_app.py` (ya configura `ssl_cert_reqs`) o agregar `?ssl_cert_reqs=required` a la URL |
| `401` intermitente en el polling | `ACCESS_TOKEN_EXPIRE_MINUTES=1` en local | El script re-loguea solo; en staging usar 15–30 minutos |
| `chat 500` / `suggestion 500` | `GOOGLE_AI_API_KEY` inválida, cuota o modelo no disponible | Revisar la key y `AI_MODEL_EMBEDDING`/modelos de chat |
| `chat` responde sin citar el documento | No hay chunks o la consulta no recupera | Verificar `search` primero y el proyecto correcto |

## Limpieza

`CLEANUP=1` primero archiva (`DELETE /proyectos/{id}`) y después hace el hard delete
(`DELETE /proyectos/{id}/permanent`); el hard delete rechaza proyectos no archivados.
Si no se usó `CLEANUP=1`, borrar el proyecto desde la API (archivar + permanent) o desde SQL:

```sql
DELETE FROM projects WHERE name LIKE 'RAG Staging Smoke %';
```

Los `document_chunks` y `attachments` se eliminan en cascada. El usuario de prueba puede
quedar o eliminarse manualmente.
