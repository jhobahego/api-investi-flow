# Protección de costos para Gemini en FastAPI

Guía para implementar rate limit y topes de gasto con `limits` + Redis, usando solo tiers gratuitos.

> Los datos de precios y cuotas de terceros cambian seguido. Los valores de esta guía se revisaron en octubre de 2026 en fuentes públicas; confírmalos en las páginas oficiales antes de decidir.

---

## 1. Idea general: defensa en capas

Ninguna capa sola protege la factura. La idea es que cada una cubra el fallo de la anterior:

| Capa | Dónde vive | Qué frena | ¿Corta el gasto de verdad? |
|---|---|---|---|
| 0. Prefiltro local por IP | Memoria del proceso | Floods obvios, sin gastar comandos de Redis | Parcial |
| 1. Rate limit por IP y usuario | Redis (`limits`) | Abuso individual | Sí, a nivel de app |
| 2. Presupuesto global de tokens/día | Redis (`limits`) | Abuso distribuido (IPs rotando, muchas cuentas) | Sí, a nivel de app |
| 3. Validación de tamaño + `max_output_tokens` | Código | Peticiones individuales carísimas | Sí |
| 4. Spend cap del proyecto en AI Studio | Google | Todo lo anterior si falla | **Sí, es el tope duro** |
| 5. Budget alerts + alertas de uso | Google Cloud | Avisarte a tiempo | **No**, solo notifican |

Dato clave: los **Cloud Billing budgets no limitan el gasto**, solo envían alertas. El tope duro en Google es el *Project Spend Cap* de AI Studio (sección 6).

---

## 2. Redis en producción (tier gratuito)

Hoy tienes Redis solo en local. Como tu proyecto es FastAPI + Gemini, estas son las opciones realistas:

| Opción | Free tier | Ventajas | Cuidado |
|---|---|---|---|
| **Upstash Redis** (recomendada) | 256 MB y 500 000 comandos/mes, sin tarjeta | Funciona desde cualquier hosting, TLS incluido, dashboard con comandos en vivo | El límite de **comandos/mes** es el cuello de botella (ver 2.1) |
| **Redis Cloud (Essentials gratis)** | 30 MB, 30 conexiones concurrentes, ~100 ops/seg | Redis "de verdad", sin tope mensual de comandos | Sin replicación (sin failover); 30 conexiones obliga a limitar el pool por worker |
| **Redis en el mismo servidor** (contenedor o servicio local) | Gratis si ya pagas/usas una VM o VPS | Latencia mínima, sin límites de comandos | Solo sirve si todos tus workers están en la misma máquina; tú lo mantienes |

**Recomendación:** empieza con **Upstash**. Es la opción con menos fricción y, si tu hosting escala a varias instancias (Cloud Run, Fly, Render, etc.), el estado compartido es obligatorio. Si tu tráfico crece y el cupo de comandos se queda corto, pasa a Redis en tu propio servidor o a un plan de pago pequeño.

**Sin Redis aún (plan B temporal):** un solo worker (`--workers 1`) con `MemoryStorage` funciona, pero pierdes los contadores en cada reinicio y no escala a varias instancias. Úsalo solo mientras configuras Redis.

### 2.1 Presupuesto de comandos en Upstash

Cada `hit` de `limits` ejecuta de 1 a unos pocos comandos en Redis, según la estrategia. Calcula tu consumo así:

```
comandos_mes ≈ peticiones_mes × hits_por_petición × comandos_por_hit
```

Con 4 hits por petición y ~2 comandos por hit, 500 000 comandos alcanzan para unas 60 000 peticiones al mes (~2 000/día). Mídelo en el dashboard de Upstash durante las primeras horas y ajusta.

Consecuencias de diseño (ya aplicadas en el código de abajo):

1. **Pocas reglas, bien elegidas.** El presupuesto de tokens ya cubre los límites diarios de peticiones, así que no hace falta duplicarlos.
2. **Prefiltro local por IP.** Cada petición rechazada también cuesta comandos. Sin prefiltro, un atacante puede agotar tu cupo de Upstash enviando basura.
3. **Fallback en memoria** si Redis falla o se agota el cupo, para no quedarte sin protección.
4. **Solo limitar rutas que llaman a Gemini.** No uses un middleware global que cuente `/health` o `/docs`.

### 2.2 Variables de entorno

```bash
# .env (local)
RATE_LIMIT_REDIS_URL=async+redis://localhost:6379

# producción (Upstash usa TLS: nota la "s" en rediss)
RATE_LIMIT_REDIS_URL=async+rediss://default:TU_TOKEN@tu-instancia.upstash.io:6379

GEMINI_API_KEY=...
GEMINI_MODEL=el-modelo-que-uses
```

El prefijo `async+` le indica a `limits` que use el backend asíncrono. Elige la región de Upstash más cercana a tu hosting para reducir latencia, y guarda la URL en el gestor de secretos de tu plataforma, nunca en el repositorio.

---

## 3. Instalación

```bash
pip install "limits[async-redis]" google-genai
```

---

## 4. Implementación

### 4.1 `rate_limit.py`

```python
import logging
import math
import os
import time

from fastapi import HTTPException, Request
from limits import parse
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import FixedWindowRateLimiter, MovingWindowRateLimiter
from limits.storage import storage_from_string

logger = logging.getLogger("gemini-guard")

# ---------------------------------------------------------------- configuración
MAX_PROMPT_CHARS = 4_000
MAX_OUTPUT_TOKENS = 1_024

LOCAL_IP_PREFILTER = parse("60/minute")        # memoria local, 0 comandos Redis
IP_PER_MIN = parse("20/minute")                # Redis
USER_PER_MIN = parse("5/minute")               # Redis
USER_TOKENS_DAY = parse("200000/day")          # Redis, presupuesto por usuario
GLOBAL_TOKENS_DAY = parse("3000000/day")       # Redis, techo de gasto global

# ---------------------------------------------------------------- almacenamiento
_redis = storage_from_string(
    os.environ.get("RATE_LIMIT_REDIS_URL", "async+redis://localhost:6379"),
    socket_connect_timeout=1,   # no colgar la petición si Redis no responde
    socket_timeout=1,
    max_connections=5,          # importante con el plan de 30 conexiones de Redis Cloud
)
_memory = MemoryStorage()

_REDIS = {
    "moving": MovingWindowRateLimiter(_redis),   # preciso, para ventanas cortas
    "fixed": FixedWindowRateLimiter(_redis),     # barato, para ventanas largas
}
_MEM = {
    "moving": MovingWindowRateLimiter(_memory),
    "fixed": FixedWindowRateLimiter(_memory),
}
_LOCAL = MovingWindowRateLimiter(_memory)


# ---------------------------------------------------------------- utilidades
def estimate_tokens(text: str) -> int:
    """Estimación conservadora (~3 caracteres por token)."""
    return max(1, len(text) // 3)


def client_ip(request: Request) -> str:
    # Con uvicorn --proxy-headers y --forwarded-allow-ips bien configurado,
    # request.client.host ya es la IP real. No leas X-Forwarded-For a mano.
    return request.client.host if request.client else "unknown"


async def _hit(kind: str, item, ids: tuple, cost: int) -> bool:
    if kind == "local":
        return await _LOCAL.hit(item, *ids, cost=cost)
    try:
        return await _REDIS[kind].hit(item, *ids, cost=cost)
    except Exception:
        # Redis caído o cupo agotado: seguimos protegidos con memoria local.
        logger.exception("Redis no disponible, usando límites en memoria")
        return await _MEM[kind].hit(item, *ids, cost=cost)


async def _retry_after(kind: str, item, ids: tuple) -> int:
    try:
        strategy = _LOCAL if kind == "local" else _REDIS[kind]
        stats = await strategy.get_window_stats(item, *ids)
        return max(1, math.ceil(stats.reset_time - time.time()))
    except Exception:
        return 60


# ---------------------------------------------------------------- enforcement
async def enforce_gemini_limits(request: Request, user_id: str, prompt: str) -> None:
    if len(prompt) > MAX_PROMPT_CHARS:
        raise HTTPException(413, f"El prompt supera {MAX_PROMPT_CHARS} caracteres")

    ip = client_ip(request)
    cost = estimate_tokens(prompt) + MAX_OUTPUT_TOKENS  # peor caso de la petición

    # Orden: lo más barato y específico primero; lo global al final, para que
    # las peticiones rechazadas antes no consuman el presupuesto global.
    checks = [
        ("local",  LOCAL_IP_PREFILTER, ("ip-local", ip),         1,    429, "Demasiadas peticiones"),
        ("moving", IP_PER_MIN,         ("ip", ip),               1,    429, "Demasiadas peticiones desde tu IP"),
        ("moving", USER_PER_MIN,       ("user", user_id),        1,    429, "Demasiadas peticiones, espera un momento"),
        ("fixed",  USER_TOKENS_DAY,    ("user-tokens", user_id), cost, 429, "Alcanzaste tu cuota diaria"),
        ("fixed",  GLOBAL_TOKENS_DAY,  ("global-tokens",),       cost, 503, "Servicio temporalmente saturado"),
    ]

    for kind, item, ids, c, status, message in checks:
        if not await _hit(kind, item, ids, c):
            logger.warning("Límite excedido: %s %s", ids[0], ids[1:] or "")
            retry = await _retry_after(kind, item, ids)
            raise HTTPException(status, message, headers={"Retry-After": str(retry)})
```

### 4.2 `gemini_client.py`

```python
import asyncio
import logging
import os

from google import genai
from google.genai import types

from rate_limit import MAX_OUTPUT_TOKENS

logger = logging.getLogger("gemini-guard")

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = os.environ["GEMINI_MODEL"]

_in_flight = asyncio.Semaphore(5)   # máximo 5 llamadas simultáneas a Gemini


async def call_gemini(prompt: str) -> str:
    async with _in_flight:
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    temperature=0.7,
                ),
            ),
            timeout=30,
        )

    usage = response.usage_metadata
    if usage:
        # Estos logs son tu fuente de verdad para auditar costos reales
        logger.info(
            "gemini_usage prompt=%s output=%s total=%s",
            usage.prompt_token_count,
            usage.candidates_token_count,
            usage.total_token_count,
        )
    return response.text
```

Si tu modelo usa "thinking", esos tokens de razonamiento también se facturan. Revisa en la documentación de tu modelo cómo limitarlos (por ejemplo, un presupuesto de thinking).

### 4.3 `main.py`

```python
from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel, Field

from gemini_client import call_gemini
from rate_limit import MAX_PROMPT_CHARS, enforce_gemini_limits

app = FastAPI()


class ChatIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=MAX_PROMPT_CHARS)


async def get_current_user(request: Request) -> str:
    # Sustituye por tu autenticación real (JWT, API key, sesión...).
    # Debe devolver un identificador estable del usuario.
    ...


@app.post("/chat")
async def chat(body: ChatIn, request: Request, user_id: str = Depends(get_current_user)):
    await enforce_gemini_limits(request, user_id, body.prompt)
    return {"text": await call_gemini(body.prompt)}
```

Si tienes endpoints sin autenticación que llaman a Gemini, usa la IP como identificador y baja los límites: son los más fáciles de abusar.

### 4.4 Limitar el tamaño del body

Pydantic valida `max_length` después de leer el body completo. Corta antes en el proxy o servidor:

- Nginx: `client_max_body_size 16k;`
- Sin proxy: un middleware que rechace con 413 si `Content-Length` supera tu máximo.

---

## 5. Cómo dimensionar los límites

Parte de cuánto estás dispuesto a gastar, no de cuánto tráfico esperas:

```
tokens_globales_día = (presupuesto_mensual_USD / 30) / precio_por_token
```

Consulta el precio por millón de tokens (entrada y salida) de tu modelo en la página oficial de precios de Gemini y usa el más caro de los dos para ser conservador.

| Límite | Valor de ejemplo | Cómo ajustarlo |
|---|---|---|
| `GLOBAL_TOKENS_DAY` | 3 000 000 | Resultado de la fórmula anterior; es tu techo diario |
| `USER_TOKENS_DAY` | 200 000 | ~5–10 % del global, para que pocos usuarios no lo agoten |
| `USER_PER_MIN` | 5 | Lo que un humano usa de verdad |
| `IP_PER_MIN` | 20 | Mayor que el de usuario (varias personas pueden compartir IP) |
| `LOCAL_IP_PREFILTER` | 60 | Solo para cortar floods antes de tocar Redis |
| `MAX_PROMPT_CHARS` | 4 000 | Según tu caso de uso real |
| `MAX_OUTPUT_TOKENS` | 1 024 | Lo mínimo que tu producto necesita |

Con estos valores, cada petición se cuenta por su peor caso (prompt estimado + `MAX_OUTPUT_TOKENS`). Así el tope global protege el gasto aunque los usuarios no consuman todo.

**Reglas opcionales** si tu Redis tiene margen de comandos: límite diario de peticiones por usuario, límite por IP diario, límite por hora.

---

## 6. Google: topes duros, presupuestos y alertas

### 6.1 Tope duro: Project Spend Cap en AI Studio (hazlo primero)

1. Entra a Google AI Studio → pestaña **Spend** → **Monthly spend cap**.
2. Define un tope mensual **bajo** para el proyecto (empieza con el monto que no te dolería perder).
3. Usa un **proyecto dedicado** para esta API, así el tope no se comparte con otras cosas.

Notas:

- Además existe un tope por nivel (tier) a nivel de cuenta de facturación; en el Tier 1 fue de 250 USD/mes según las fuentes revisadas. Confírmalo en tu cuenta.
- Cuando se alcanza un tope, **las peticiones se pausan hasta el siguiente mes**. Es una protección de último recurso, no un rate limit.
- Puede no estar disponible si tu proyecto está ligado a una cuenta de facturación por factura (invoiced). Verifícalo.
- Tómalo como una red de seguridad, no como tu control principal: asume que puede haber retraso entre el gasto real y el corte. Por eso el límite en tu app sigue siendo necesario.

### 6.2 Cloud Billing budget con alertas (solo avisa)

Billing → Budgets & alerts → crear presupuesto para el proyecto de Gemini:

| Umbral | Tipo | Para qué |
|---|---|---|
| 25 % | Gasto real | Aviso temprano, útil para detectar un uso anómalo en la primera semana |
| 50 % | Gasto real | Revisión de rutina |
| 75 % | Gasto real | Empieza a investigar |
| 90 % | Gasto real | Acción inmediata |
| 100 % | Gasto real | Crítico |
| 100 % | **Pronosticado** | Te avisa antes de llegar, si el ritmo actual lo superará |

Configura notificaciones por correo a varios administradores, no solo a ti. Opcionalmente conecta el presupuesto a un tema de Pub/Sub para automatizar acciones.

### 6.3 Alertas de uso (Cloud Monitoring)

Los budgets reaccionan tarde porque el gasto se reporta con retraso. Complementa con alertas sobre el **conteo de peticiones** de la API (servicio `generativelanguage.googleapis.com`):

- Peticiones por minuto por encima de tu máximo esperado durante 5 minutos.
- Pico repentino frente al promedio de las últimas horas.
- Ratio alto de errores 429 (indica que alguien está chocando con tus límites o con las cuotas de Google).

### 6.4 Cuotas de la API

En Google Cloud Console → IAM & Admin → **Quotas**, filtra por la API de Gemini (Generative Language) y, si la consola lo permite para tu modelo, baja la cuota de peticiones por minuto del proyecto a un valor cercano a tu uso real.

### 6.5 Interruptor de emergencia (opcional, avanzado)

Un presupuesto → Pub/Sub → Cloud Function puede deshabilitar la facturación del proyecto al llegar al 100 %. Úsalo solo en un proyecto **dedicado** a Gemini: desactivar la facturación detiene todos los servicios de pago de ese proyecto. Pub/Sub y Cloud Functions tienen cupos gratuitos, pero verifica los límites actuales.

### 6.6 Higiene de la API key (donde ocurren los incidentes grandes)

Los casos más graves de facturas inesperadas reportados en 2026 venían de claves filtradas, no de rate limits mal configurados.

- La key vive **solo en el backend** (variable de entorno o gestor de secretos). Nunca en el frontend ni en bundles de Vite/Next.
- Restringe la key a la API de Gemini y, si tu servidor tiene IP fija, por IP.
- Usa una key distinta por entorno (dev y prod).
- Rótala de inmediato ante cualquier sospecha y revisa el historial de uso.

---

## 7. Alertas propias en tu app (gratis)

- Registra cada llamada con `gemini_usage` (ya incluido arriba) y llévalo a Cloud Logging o al visor de logs de tu hosting.
- Envía un aviso a un webhook gratuito (Discord, Telegram, Slack) cuando se rechace por `GLOBAL_TOKENS_DAY` (503): significa que llegaste a tu techo diario.
- Crea una métrica basada en logs que cuente los `Límite excedido` por hora; un salto indica un intento de abuso.

---

## 8. Despliegue

```bash
# Si estás detrás de un proxy/balanceador, confía solo en su IP:
uvicorn main:app --host 0.0.0.0 --port 8000 \
  --proxy-headers --forwarded-allow-ips="IP_DE_TU_PROXY"
```

- **Varios workers o instancias:** ya no hay problema porque el estado vive en Redis. Con Redis Cloud gratis (30 conexiones), mantén `max_connections` bajo × número de workers < 30.
- **Autoescalado (Cloud Run, Fly, Render...):** Redis compartido es obligatorio; sin él, el límite real se multiplica por el número de instancias.
- **No confíes en `X-Forwarded-For` directamente:** un cliente puede falsificarlo y saltarse el límite por IP.

---

## 9. Probar que funciona

```bash
# Con USER_PER_MIN = 5 deberías ver cinco 200 y luego 429
for i in $(seq 1 8); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer TU_TOKEN" \
    -d '{"prompt":"hola"}'
done
```

Otras pruebas recomendadas:

- Prompt de `MAX_PROMPT_CHARS + 1` caracteres → 413.
- Apaga Redis local y repite: debe seguir limitando con el fallback en memoria y dejar un error en los logs.
- Revisa la cabecera `Retry-After` en una respuesta 429.
- Sube temporalmente `GLOBAL_TOKENS_DAY` a un valor muy bajo para verificar el 503.

---

## 10. Checklist final

- [ ] Spend cap mensual configurado en AI Studio (proyecto dedicado)
- [ ] Budget con alertas al 25/50/75/90/100 % y pronosticado
- [ ] Alerta de Cloud Monitoring sobre peticiones por minuto
- [ ] API key solo en backend, restringida, y rotada si hubo sospecha
- [ ] Redis de producción creado (Upstash recomendado) y URL en secretos
- [ ] `max_output_tokens`, longitud máxima del prompt y timeout configurados
- [ ] Límites por IP, por usuario y global activos y probados
- [ ] Prefiltro local y fallback en memoria probados
- [ ] Logs de uso de tokens y alerta cuando se llegue al techo global
- [ ] Consumo de comandos de Upstash revisado tras las primeras 24 horas

---

## 11. Datos que ayudarían a afinar la guía

Para ajustar los valores y recomendar la opción de Redis exacta, falta saber:

1. **Dónde despliegas** (Cloud Run, Render, Railway, Fly, VPS, otro).
2. **Cómo autenticas** a los usuarios (JWT, API key, sesión, o sin autenticación).
3. **Cuántos workers/instancias** esperas y cuántas peticiones al día.
4. **Qué modelo de Gemini usas** y cuánto estás dispuesto a gastar al mes.
