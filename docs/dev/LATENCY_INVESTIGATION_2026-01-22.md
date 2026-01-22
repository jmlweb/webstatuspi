# Investigación de Latencia Alta - 2026-01-22

## Resumen Ejecutivo

Los tiempos de respuesta del monitor pasaron de **200-500ms** a **1000-2000ms**. La investigación identificó dos factores principales:

1. **OpenSSL 3.5 con algoritmos post-cuánticos**: El nuevo default `X25519MLKEM768` es muy lento en ARM
2. **Doble conexión SSL**: El monitor hace dos handshakes SSL por cada URL HTTPS

## Hallazgos

### 1. Entorno de la Raspberry Pi

| Componente | Valor |
|------------|-------|
| CPU | ARMv6-compatible (700MHz) |
| RAM | 427MB total, ~150MB usado |
| OpenSSL | 3.5.4 (30 Sep 2025) |
| Python | 3.x (sistema) |

### 2. Diagnóstico de Red

```
Ping 8.8.8.8: 10.8ms (excelente)
DNS resolution: 18ms (excelente)
```

**La red local no es el problema.**

### 3. Análisis de SSL Handshake

OpenSSL 3.5+ usa por defecto el algoritmo híbrido post-cuántico `X25519MLKEM768`:

```
SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384 / X25519MLKEM768
```

| Configuración | Tiempo SSL |
|---------------|------------|
| Default (X25519MLKEM768) | ~700-1400ms |
| P-256 forzado | ~200-350ms |

### 4. Arquitectura del Monitor

El monitor realiza **dos conexiones SSL separadas** por cada URL HTTPS:

1. `_get_ssl_cert_info()` - Extrae información del certificado (línea ~119)
2. `_opener.open()` - Request HTTP real (línea ~404)

**Tiempo total = SSL handshake × 2 + HTTP response**

### 5. Fix Aplicado

Se añadió configuración para forzar curvas EC clásicas:

```python
# monitor.py - líneas 73-94
_SSL_ECDH_CURVE = "prime256v1"

def _create_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    try:
        ctx.set_ecdh_curve(_SSL_ECDH_CURVE)
    except (ValueError, ssl.SSLError):
        pass
    return ctx
```

Cambios:
- Nuevo `_https_handler` con contexto optimizado para `_opener`
- `_get_ssl_cert_info()` ahora usa `_create_ssl_context()`

### 6. Resultados Post-Fix

| Métrica | Antes | Después (manual) | Después (monitor) |
|---------|-------|------------------|-------------------|
| SSL standalone | ~900ms | ~220-350ms | N/A |
| check_url total | ~1800ms | ~400-600ms (teoría) | ~1000-2000ms (variable) |

**Nota:** Los resultados del monitor siguen variables debido a:
- Contención de CPU en single-core
- Dos conexiones SSL por URL
- Variabilidad de red/servidor

## Commits Potencialmente Relacionados

| Commit | Descripción | Posible Impacto |
|--------|-------------|-----------------|
| `046daaa` | feat(monitor): add SSL certificate monitoring | **ALTO** - Añade `_get_ssl_cert_info()` que hace una conexión SSL adicional |
| `7fbc70d` | feat(monitor): add DNS monitoring | Bajo - Añade checks DNS |
| `331a756` | feat(monitor): add TCP monitoring | Bajo - Añade checks TCP |

**El commit `046daaa` es el más probable causante** ya que añadió la verificación de certificados SSL, duplicando las conexiones SSL por URL HTTPS.

## Cambio en el Sistema Operativo

Es probable que la Pi se actualizara recientemente a Debian con OpenSSL 3.5.x, que habilita algoritmos post-cuánticos por defecto. Esto explicaría el aumento repentino de latencia incluso sin cambios de código.

## Recomendaciones

### Corto Plazo (aplicado)
- ✅ Forzar curvas EC clásicas (`prime256v1`) en lugar de híbridas post-cuánticas

### Mediano Plazo (requiere desarrollo)
1. **Reusar conexión SSL**: Extraer info del certificado de la misma conexión HTTP
2. **Hacer check de cert opcional**: Configurar por URL si se quiere verificar SSL
3. **Cache de certificados**: Cachear info de certificado por X minutos

### Largo Plazo
1. Evaluar si la Pi 1B+ es suficiente para el workload actual
2. Considerar reducir frecuencia de checks para URLs con SSL cert monitoring

## Archivos Modificados

- `webstatuspi/monitor.py`:
  - Añadida función `_create_ssl_context()`
  - Modificado `_opener` para usar contexto optimizado
  - Modificado `_get_ssl_cert_info()` para usar contexto optimizado

## Comandos para Verificar

```bash
# Ver tiempos actuales
curl -s http://localhost:8080/status | python3 -m json.tool | grep response_time

# Test SSL manual
python3 -c "
import ssl, socket, time
ctx = ssl.create_default_context()
ctx.set_ecdh_curve('prime256v1')
start = time.time()
with socket.create_connection(('jmlweb.es', 443), timeout=10) as s:
    with ctx.wrap_socket(s, server_hostname='jmlweb.es') as ss:
        print(f'SSL: {(time.time()-start)*1000:.0f}ms')
"
```

## Conclusión

La latencia alta se debe principalmente a:
1. **OpenSSL 3.5 con post-quantum por defecto** (resuelto parcialmente con fix)
2. **Doble conexión SSL** introducida en commit `046daaa` (requiere refactorización)

El fix aplicado debería reducir los tiempos, pero la arquitectura de doble conexión SSL sigue siendo un factor limitante en hardware tan restringido.
