# Arquitectura: Separación del Servidor Web

## Propuesta

Instalar un servidor web ligero (nginx, lighttpd, Caddy) que sirva los assets estáticos y el HTML, mientras que el script Python solo se encarga de:
- Monitorear URLs
- Actualizar la base de datos
- Exponer una API JSON en un puerto interno

**Beneficio principal**: Reiniciar el script Python sin cortar la conexión del servidor web.

## Análisis de Opciones

### Opción 1: Nginx como Reverse Proxy + Servidor Estático

**Arquitectura**:
```
Cliente → Nginx (puerto 80/443) → Python API (puerto interno 8080)
                ↓
         Assets estáticos (HTML/CSS/JS)
```

**Ventajas**:
- ✅ Servidor web independiente (no se cae con Python)
- ✅ Mejor rendimiento para servir estáticos
- ✅ SSL/TLS más fácil de configurar
- ✅ Reverse proxy para la API JSON
- ✅ Nginx es muy ligero (~5-10MB RAM)

**Desventajas**:
- ❌ Dependencia externa (hay que instalar nginx)
- ❌ Más complejidad (configuración adicional)
- ❌ Va contra la filosofía "zero dependencies" del proyecto
- ❌ El dashboard actualmente se genera dinámicamente con datos iniciales (SSR)

**Consumo de recursos** (Pi 1B+):
- RAM: +5-10MB (nginx)
- CPU: Mínimo (nginx es muy eficiente)
- Almacenamiento: ~1MB (binario nginx)

### Opción 2: Lighttpd (Más Ligero que Nginx)

**Ventajas**:
- ✅ Aún más ligero que nginx (~3-5MB RAM)
- ✅ Configuración más simple
- ✅ Buen rendimiento para estáticos

**Desventajas**:
- ❌ Menos común (menos documentación)
- ❌ Misma complejidad que nginx
- ❌ Mismo problema con SSR del dashboard

### Opción 3: Caddy (Automático SSL)

**Ventajas**:
- ✅ SSL automático con Let's Encrypt
- ✅ Configuración muy simple

**Desventajas**:
- ❌ Más pesado que nginx (~15-20MB RAM)
- ❌ No es ideal para Pi 1B+

### Opción 4: Servidor Web Integrado (Actual)

**Ventajas**:
- ✅ Zero dependencies
- ✅ Todo en un solo proceso
- ✅ Dashboard con SSR (datos iniciales embebidos)
- ✅ Simplicidad máxima

**Desventajas**:
- ❌ Reiniciar Python = cortar conexiones web
- ❌ `http.server` es menos eficiente que nginx para estáticos

## Consideraciones Técnicas

### Dashboard con Server-Side Rendering (SSR)

El dashboard actual (`api.py:716-739`) genera HTML dinámicamente con datos iniciales:

```python
def _handle_dashboard(self) -> None:
    # Genera HTML con datos iniciales de la BD
    statuses = get_latest_status(self.db_conn)
    response = _build_status_response(statuses, internet_status)
    initial_data = json.dumps(response)
    html = HTML_DASHBOARD.replace("__INITIAL_DATA__", initial_data)
```

**Problema**: Si separamos el servidor web, necesitaríamos:
1. Generar HTML estático periódicamente (archivo en disco)
2. O hacer que nginx haga proxy a Python para `/` y servir estáticos para assets
3. O cambiar a client-side rendering puro (sin SSR)

### API JSON

La API JSON (`/status`, `/history`, etc.) debe seguir viniendo de Python porque:
- Lee datos de la base de datos
- Calcula estadísticas en tiempo real
- Requiere lógica de negocio

**Solución**: Nginx haría reverse proxy a Python para endpoints de API.

## Recomendación

### Para Desarrollo/Testing: Mantener Arquitectura Actual

**Razones**:
1. **Simplicidad**: Un solo proceso, fácil de depurar
2. **Zero dependencies**: Alineado con la filosofía del proyecto
3. **Suficiente**: Para uso personal/small scale, `http.server` es suficiente
4. **RAM limitada**: Cada MB cuenta en Pi 1B+

### Para Producción/Deployment: Considerar Nginx

**Cuándo tiene sentido**:
- ✅ Necesitas alta disponibilidad (no cortar conexiones)
- ✅ Múltiples usuarios concurrentes
- ✅ SSL/TLS requerido
- ✅ Tienes RAM suficiente (~10MB extra no es problema)

**Implementación sugerida**:

1. **Nginx como reverse proxy**:
   ```nginx
   server {
       listen 80;
       server_name webstatuspi.lan;
       
       # Dashboard (generado por Python con SSR)
       location / {
           proxy_pass http://127.0.0.1:8080;
           proxy_set_header Host $host;
       }
       
       # API endpoints
       location /status {
           proxy_pass http://127.0.0.1:8080;
       }
       
       # Assets estáticos (si se separan)
       location /static/ {
           alias /opt/webstatuspi/static/;
       }
   }
   ```

2. **Python en puerto interno** (8080):
   - Cambiar `api.port` a 8080 en config
   - Solo accesible desde localhost
   - Nginx expone puerto 80/443

3. **Dashboard estático** (opcional):
   - Generar HTML estático periódicamente
   - O mantener SSR vía proxy

## Alternativa: Mejora del Servidor Actual

En lugar de separar, podríamos mejorar la arquitectura actual:

### Opción A: Hot Reload de Configuración

Permitir recargar configuración sin reiniciar el servidor:
- SIGHUP para recargar config
- Mantener servidor web corriendo
- Solo reiniciar el loop de monitoreo

### Opción B: Servidor Web como Proceso Separado (Python)

Crear un proceso Python separado solo para el servidor web:
- Proceso 1: Monitor (monitorea URLs, actualiza BD)
- Proceso 2: API Server (sirve web, lee BD)
- Comparten la misma base de datos SQLite

**Ventajas**:
- ✅ Sin dependencias externas
- ✅ Reiniciar monitor sin afectar servidor web
- ✅ Mantiene SSR del dashboard

**Desventajas**:
- ❌ Más complejidad (dos procesos)
- ❌ Más consumo de RAM (dos procesos Python)

## Solución Implementada: Service Worker con Stale-While-Revalidate

### Contexto

El proyecto usa cloudflared para exponer la aplicación a través de `https://status.jmlweb.es`. El problema era que al ejecutar `sudo systemctl restart webstatuspi`, cloudflared perdía conexión al backend y Cloudflare devolvía error 502.

### Arquitectura Actual

```
Cliente → Cloudflare CDN → cloudflared → Python (8080)
                              ↓
                    Service Worker (navegador)
                              ↓
                         Cache API
```

### Solución: Mejora del Service Worker

Se modificó el Service Worker para usar **Stale-While-Revalidate** para el HTML del dashboard:

1. **HTML (ruta `/`)**: Sirve desde cache inmediatamente, actualiza en background
   - Si hay cache → responde al instante (0ms)
   - Fetch en background para actualizar cache (no bloquea)
   - Si no hay cache → espera network (primera visita)
   - Si network falla sin cache → página offline con auto-refresh

2. **API (`/status`, `/history`)**: Network-first con timeout corto (3s)
   - Intenta network primero con timeout de 3s
   - Si falla → sirve desde cache con header `X-From-Cache: true`
   - El JS detecta este header y muestra "⚡ RECONNECTING"

3. **Assets estáticos**: Cache-first (sin cambios)

### Comportamiento Durante Reinicio

| Fase | Duración | Lo que ve el usuario |
|------|----------|----------------------|
| Carga inicial | 0ms | Dashboard desde cache (datos del último fetch) |
| Primer poll | ~3s | Banner "⚡ RECONNECTING - Showing cached data" |
| Servidor vuelve | Variable | Banner desaparece, datos frescos |

### Código Modificado

**`_pwa.py`** - Service Worker:
- HTML: Stale-While-Revalidate con timeout 5s
- API: Network-first con timeout 3s y header `X-From-Cache`

**`_dashboard/_js_core.py`** - fetchStatus():
- Detecta header `X-From-Cache`
- Muestra mensaje diferenciado: "RECONNECTING" vs "OFFLINE"

### Ventajas de Esta Solución

- ✅ Zero dependencies externas
- ✅ No requiere nginx ni cambios de arquitectura
- ✅ Funciona con cloudflared sin modificaciones
- ✅ El usuario nunca ve 502 (solo banner temporal)
- ✅ Datos máximo 10s desactualizados durante reconexión
- ✅ Auto-refresh si no hay cache y servidor caído

### Limitaciones

- ⚠️ Requiere que el usuario haya visitado antes (para tener cache)
- ⚠️ Primera visita durante reinicio ve página offline temporal
- ⚠️ Datos pueden estar hasta 10s desactualizados durante reconexión

## Conclusión

**Solución elegida**: Service Worker con Stale-While-Revalidate.

Esta solución mantiene la filosofía zero-dependencies del proyecto, funciona transparentemente con cloudflared, y elimina los errores 502 durante reinicios sin añadir complejidad de infraestructura.

**Alternativas descartadas**:
- Nginx: Añade dependencia externa innecesaria
- Dos procesos Python: Más complejo, más RAM
- Hot reload con SIGHUP: No resuelve actualizaciones de código
