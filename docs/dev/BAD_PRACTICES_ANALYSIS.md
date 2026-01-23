# Análisis de Malas Prácticas - WebStatusPi

**Fecha**: 2026-01-23  
**Prioridad**: Ahorro de recursos para Raspberry Pi 1B+ (512MB RAM, 700MHz single-core)

Este documento identifica malas prácticas en el código, priorizando optimizaciones para hardware limitado sobre prácticas generales de desarrollo.

---

## 🔴 Críticas (Alto Impacto en Recursos)

### 1. Uso de `requests` en `alerter.py` (Inconsistencia con filosofía del proyecto)

**Problema**:  
El proyecto usa `urllib` (stdlib) para todas las checks principales para ahorrar recursos, pero `alerter.py` usa `requests` para webhooks. `requests` es más pesado:
- ~2-3MB adicionales de RAM
- Dependencia externa innecesaria
- Overhead de parsing/encoding más complejo

**Ubicación**: `webstatuspi/alerter.py:9, 180, 299, 378`

**Impacto**: 
- RAM: +2-3MB (significativo en 512MB total)
- CPU: Parsing adicional de headers/body
- Dependencia: Aumenta tamaño del paquete

**Recomendación**:  
Reemplazar `requests.post()` con `urllib.request.urlopen()` en `alerter.py`. El código ya tiene experiencia con `urllib` en `monitor.py`.

**Justificación para Pi 1B+**:  
Priorizar ahorro de RAM sobre conveniencia de API. `urllib` es suficiente para POST con JSON.

---

### 2. Queries SQL extremadamente complejas en `database.py`

**Problema**:  
Las queries en `_fetch_latest_status_from_db()` y `get_latest_status_by_name()` usan 7 CTEs (Common Table Expressions) anidados:
- `latest_checks`
- `stats_24h`
- `percentiles_24h`
- `stddev_24h`
- `variance_24h`
- `last_downtime`
- `consecutive_failures`

**Ubicación**: `webstatuspi/database.py:313-499, 552-739`

**Impacto**:
- CPU: Queries pueden tomar 6-11 segundos en Pi 1B+ (según comentarios en código)
- I/O: Múltiples scans de tabla `checks`
- Memoria: SQLite debe mantener resultados intermedios en RAM

**Recomendación**:  
Aunque el código implementa caché (stale-while-revalidate), las queries siguen siendo costosas cuando se ejecutan. Considerar:
1. Simplificar cálculos (eliminar percentiles si no son críticos)
2. Pre-calcular estadísticas en triggers o en inserción
3. Usar índices más específicos
4. Reducir ventana de 24h a 12h si es aceptable

**Justificación para Pi 1B+**:  
El caché ayuda, pero cuando se ejecuta la query bloquea el hilo principal. En hardware limitado, queries simples son preferibles.

---

### 3. Cachés sin límite de crecimiento (`RateLimiter`, `_SSLCertCache`, `_StatusCache`)

**Problema**:  
Los cachés pueden crecer indefinidamente:
- `RateLimiter._requests`: Una lista por IP, nunca se limpia completamente
- `_SSLCertCache._cache`: Un entry por URL, crece con nuevas URLs
- `_StatusCache`: Solo un entry, pero `_HistoryCache` crece por URL

**Ubicación**: 
- `webstatuspi/api.py:49-102` (RateLimiter)
- `webstatuspi/monitor.py:157-201` (_SSLCertCache)
- `webstatuspi/database.py:41-112` (_StatusCache, _HistoryCache)

**Impacto**:
- RAM: Crecimiento sin límite puede consumir memoria
- CPU: Limpieza periódica requiere iterar sobre todos los entries

**Recomendación**:  
Implementar límites máximos y políticas de evicción (LRU):
- `RateLimiter`: Limpiar IPs sin actividad > 1 hora
- `_SSLCertCache`: Máximo 50 URLs, evict LRU
- `_HistoryCache`: Máximo 10 URLs, evict LRU

**Justificación para Pi 1B+**:  
En 512MB RAM, cachés sin límite son peligrosos. Mejor perder algunos hits de caché que quedarse sin memoria.

---

### 4. Threads daemon sin control en revalidación de caché

**Problema**:  
En `database.py:537-543`, se crean threads daemon para revalidar caché sin límite:

```python
thread = threading.Thread(
    target=_revalidate_cache_background,
    args=(conn,),
    daemon=True,
)
thread.start()
```

Si hay muchas requests concurrentes, pueden crearse muchos threads simultáneamente.

**Ubicación**: `webstatuspi/database.py:536-543`

**Impacto**:
- RAM: Cada thread consume ~8MB stack (default Python)
- CPU: Context switching entre muchos threads
- I/O: Múltiples queries SQL concurrentes compiten por el lock

**Recomendación**:  
Usar un solo thread de revalidación con un queue, o un semáforo para limitar threads concurrentes a 1.

**Justificación para Pi 1B+**:  
En single-core, muchos threads compiten por CPU. Mejor serializar revalidaciones.

---

## 🟡 Moderadas (Impacto Medio)

### 5. Lectura completa del body para validación (hasta 1MB)

**Problema**:  
En `monitor.py:532`, se lee hasta 1MB del body para validación de keyword/JSON:

```python
body_bytes = response.read(MAX_BODY_SIZE)
body = body_bytes.decode("utf-8")
```

**Ubicación**: `webstatuspi/monitor.py:531-551`

**Impacto**:
- RAM: Hasta 1MB por check concurrente (con MAX_WORKERS=3, hasta 3MB)
- CPU: Decodificación UTF-8 de 1MB
- I/O: Leer body completo aunque solo se necesite una parte

**Recomendación**:  
Si es posible, leer incrementalmente y buscar el keyword sin cargar todo en memoria. Para JSON, usar streaming parser si está disponible.

**Justificación para Pi 1B+**:  
1MB es significativo en 512MB total. Si la validación es opcional, considerar límites más bajos (256KB).

---

### 6. Uso de `time.sleep()` en lugar de mecanismos más eficientes

**Problema**:  
En `alerter.py:207, 327`, se usa `time.sleep()` para retries. Aunque está en contexto de retry (no bloquea el loop principal), podría usar `threading.Event.wait()` para ser más eficiente.

**Ubicación**: `webstatuspi/alerter.py:207, 327`

**Impacto**:
- CPU: `time.sleep()` puede ser menos eficiente que `Event.wait()` en algunos sistemas
- Responsividad: No se puede cancelar fácilmente

**Recomendación**:  
Mantener `time.sleep()` aquí es aceptable (no es crítico), pero documentar por qué no se usa `Event.wait()`.

**Justificación para Pi 1B+**:  
Impacto menor, pero en hardware limitado cada optimización cuenta.

---

### 7. Parsing de certificados SSL con múltiples bucles anidados

**Problema**:  
En `monitor.py:266-288`, el parsing de certificados SSL usa bucles anidados sobre estructuras de tuplas complejas:

```python
for item in issuer_tuple:
    if isinstance(item, tuple) and len(item) > 0:
        first = item[0]
        if isinstance(first, tuple) and len(first) == 2:
            issuer_dict[str(first[0])] = str(first[1])
```

**Ubicación**: `webstatuspi/monitor.py:266-288`

**Impacto**:
- CPU: Parsing complejo en cada check SSL (aunque está cachado)
- Legibilidad: Código difícil de mantener

**Recomendación**:  
Extraer a función helper con mejor manejo de errores. El impacto es bajo porque está cachado, pero el código es frágil.

**Justificación para Pi 1B+**:  
Impacto bajo (cachado), pero código mejorable.

---

## 🟢 Menores (Bajo Impacto, Mejoras de Código)

### 8. Validación de URL name duplicada

**Problema**:  
La validación de `url_name` se hace en múltiples lugares:
- `config.py:124-127` (validación en `__post_init__`)
- `api.py:400-431` (`_validate_url_name`)
- `security.py:118-150` (`validate_url_name`)

**Ubicación**: Múltiples archivos

**Impacto**:
- Mantenibilidad: Lógica duplicada
- CPU: Validación redundante (bajo impacto)

**Recomendación**:  
Centralizar validación en `security.py` y reutilizar.

**Justificación para Pi 1B+**:  
Impacto mínimo en recursos, pero mejora mantenibilidad.

---

### 9. Manejo de excepciones demasiado genérico

**Problema**:  
En varios lugares se captura `Exception` genérico en lugar de excepciones específicas:

```python
except Exception as e:
    return None, str(e)
```

**Ubicación**: `monitor.py:316, 633, 709, 801`, `database.py:506`

**Impacto**:
- Debugging: Dificulta identificar problemas
- Estabilidad: Puede ocultar bugs reales

**Recomendación**:  
Capturar excepciones específicas (`OSError`, `ValueError`, etc.) y dejar `Exception` solo como último recurso.

**Justificación para Pi 1B+**:  
No impacta recursos directamente, pero mejor debugging ayuda a optimizar.

---

### 10. Uso de `defaultdict` sin límite

**Problema**:  
`RateLimiter` usa `defaultdict(list)` que crea listas automáticamente. Sin límite, puede crecer con cada IP única.

**Ubicación**: `webstatuspi/api.py:63`

**Impacto**:
- RAM: Crecimiento sin límite (aunque se limpia periódicamente)

**Recomendación**:  
Ya se implementa `cleanup()` cada 100 requests, pero considerar límite máximo de IPs (ej: 1000).

**Justificación para Pi 1B+**:  
El cleanup periódico ayuda, pero un límite hard es más seguro.

---

## 📊 Resumen de Prioridades

| Prioridad | Problema | Impacto RAM | Impacto CPU | Esfuerzo Fix |
|-----------|----------|-------------|-------------|--------------|
| 🔴 Crítica | `requests` en alerter | +2-3MB | Medio | Medio |
| 🔴 Crítica | Queries SQL complejas | Bajo | Alto (6-11s) | Alto |
| 🔴 Crítica | Cachés sin límite | Variable | Bajo | Bajo |
| 🔴 Crítica | Threads sin control | +8MB c/u | Alto | Bajo |
| 🟡 Moderada | Lectura body 1MB | +1-3MB | Medio | Medio |
| 🟡 Moderada | `time.sleep()` en retries | Bajo | Bajo | Bajo |
| 🟡 Moderada | Parsing SSL complejo | Bajo | Bajo | Bajo |
| 🟢 Menor | Validación duplicada | Bajo | Bajo | Bajo |
| 🟢 Menor | Excepciones genéricas | Bajo | Bajo | Bajo |
| 🟢 Menor | `defaultdict` sin límite | Bajo | Bajo | Bajo |

---

## 🎯 Recomendaciones Prioritarias

1. **Reemplazar `requests` con `urllib`** en `alerter.py` (ahorro inmediato de 2-3MB RAM)
2. **Limitar crecimiento de cachés** con políticas LRU y límites máximos
3. **Controlar threads de revalidación** con queue o semáforo (máximo 1 concurrente)
4. **Simplificar queries SQL** o pre-calcular estadísticas (reducir complejidad de 7 CTEs a 3-4)

Estas optimizaciones priorizan el ahorro de recursos sobre "buenas prácticas" generales, que es lo correcto para hardware tan limitado como Pi 1B+.
