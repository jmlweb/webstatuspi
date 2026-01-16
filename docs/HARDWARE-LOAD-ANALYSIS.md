# Hardware Load Analysis - WebStatusPi

**Date**: 2026-01-17 (Updated)
**Hardware Target**: Raspberry Pi 1B+
**OS**: Raspberry Pi OS Lite (headless, no desktop)
**Status**: Theoretical analysis based on architecture and current configuration

## Hardware Specifications

### Raspberry Pi 1B+

- **CPU**: Single-core ARM11 @ 700MHz
- **RAM**: 512MB total
- **Network**: 10/100 Ethernet
- **Storage**: SD card (slow I/O, wear considerations)

### RAM Availability (Raspberry Pi OS Lite)

| Configuration | GPU Memory | Available for OS |
|---------------|------------|------------------|
| Desktop (default) | 128-256MB | ~256-384MB |
| **Lite (default)** | 64MB | **~448MB** |
| **Lite + gpu_mem=16** | 16MB | **~496MB** |

**Recommended**: Add `gpu_mem=16` to `/boot/config.txt` for maximum available RAM.

### Hardware Components (Phase 2)

- **0.96" OLED Display (I2C)**: 128×64 monochrome
- **Physical Button (GPIO17)**: Screen navigation
- **Buzzer (GPIO27)**: Audio alerts on failures
- **Status LEDs (GPIO22/23)**: Visual status indicators

## Current System Configuration

### Monitored URLs

- `UB_WEB`: `https://www.unobravo.com` - Interval: 60s, Timeout: 10s
- `UB_APP`: `https://app.unobravo.com` - Interval: 60s, Timeout: 10s

### System Components

- **Monitor Thread**: URL polling every 60s
- **API Server Thread**: HTTP server on port 8080 (stdlib `http.server`)
- **Display Thread**: OLED update at 1-2 FPS
- **Database**: SQLite with WAL mode (writes to WAL file)
- **Dependencies**: PyYAML, requests, Pillow, Adafruit-SSD1306, RPi.GPIO

## Resource Load Analysis

### 1. CPU (Single-core 700MHz ARM11)

#### Base System Load

- **Python Runtime**: ~5-10% CPU at idle
- **OS and services**: ~5-15% CPU (Raspberry Pi OS Lite)

**Base total**: ~10-25% CPU for base system

#### Load by Component

**Monitor Thread**:
- **HTTP check every 60s per URL**:
  - Request processing: ~10-50ms per check
  - With 2 URLs: ~20-100ms every 60s
  - **Average**: ~0.3-1.7% CPU (very low load, I/O-bound)
- **DB write**:
  - INSERT per check: ~1-5ms
  - With 2 URLs: ~2-10ms every 60s
  - **Average**: ~0.03-0.17% CPU
- **Periodic cleanup** (every N checks):
  - DELETE queries: ~10-50ms every 7 days
  - **Negligible**

**API Server Thread**:
- **Request handling**: ~5-20ms per request (DB query + JSON)
  - With low traffic (< 1 req/s): < 1% CPU
  - With moderate traffic (1-10 req/s): 1-5% CPU

**SQLite**:
- **Light queries**: < 1% CPU for simple indexed queries
- **WAL sync**: Minimized with `synchronous=NORMAL`

**Display Thread**:
- **Frame rendering**: ~5-20ms per frame
  - Font rendering: Pre-rendered characters reduce load
  - Image generation (Pillow): ~5-15ms for 128×64 monochrome
- **I2C transfer**: ~1-2ms per frame (100kHz standard mode)
- **Update frequency**: 1-2 FPS (updates only when data changes)
  - **Average**: ~2-4% CPU (within <5% target)

**GPIO Components**:
- **LED blinking**: < 0.1% CPU (simple GPIO toggling, 1Hz)
- **Buzzer PWM**: ~0.1-0.5% CPU (only during alerts)
- **Button interrupt handling**: < 0.1% CPU (interrupts, not polling)

#### Total CPU Estimate

**Current configuration (2 URLs, with display)**:
- Base system: 10-25%
- Monitoring: 0.3-1.7%
- API Server: < 1% (low traffic)
- SQLite: < 1%
- Display thread: 2-4%
- GPIO (LEDs/buzzer): < 0.5%
- **TOTAL**: ~13-32% CPU ✅

**Target configuration (10 URLs, 60s interval, with display)**:
- Base system: 10-25%
- Monitoring: 1.5-8.5%
- API Server: 1-5% (moderate traffic)
- SQLite: < 1%
- Display thread: 2-4%
- GPIO: < 0.5%
- **TOTAL**: ~15-44% CPU ✅ (acceptable)

**CPU Conclusion**: ✅ **Fully Supported** - Load is primarily I/O-bound (network, disk). Display adds ~2-4% CPU which is acceptable. 60s intervals prevent saturation.

---

### 2. RAM (512MB total, ~448-496MB available with Lite)

#### Base System Usage

- **Raspberry Pi OS Lite**: ~50-80MB (no desktop)
- **Python Runtime**: ~15-30MB

**Base available**: ~338-431MB for application (with gpu_mem=16)

#### Usage by Component

**Python Application**:
- **Base code**: ~5-10MB (loaded Python modules)
- **Config object**: < 1MB (small dataclasses)
- **Threading overhead**: ~2-5MB per thread
  - Monitor thread: 2-5MB
  - API Server thread: 2-5MB
  - Display thread: 2-5MB
  - **Total**: ~6-15MB for 3 threads

**SQLite Database**:
- **Connection pool**: ~1-2MB
- **Query cache**: < 1MB
- **WAL file**: ~1-5MB (grows with writes, cleaned periodically)
- **Indexes in memory**: < 1MB (small table)

**Libraries**:
- **requests**: ~5-10MB (including urllib3, SSL certificates)
- **PyYAML**: ~2-3MB
- **Adafruit-SSD1306**: ~1-2MB
- **RPi.GPIO**: ~1-2MB
- **Pillow**: ~5-10MB (image processing)
- **sqlite3**: Included in Python (stdlib)
- **http.server**: Included in Python (stdlib)

**Display Component**:
- **Framebuffer**: 1024 bytes = ~1KB (128×64 monochrome)
- **Font cache**: ~50-100KB (pre-rendered characters)
- **Image buffer**: ~1-5KB (temporary Pillow image)
- **Total display RAM**: ~100-200KB (negligible)

**GPIO Components**:
- **LED state**: < 1KB (simple state variables)
- **Button debounce state**: < 1KB
- **Buzzer PWM state**: < 1KB
- **Total GPIO RAM**: < 5KB (negligible)

**Runtime Overhead**:
- **Stack per thread**: ~1-2MB per thread (3 threads = ~3-6MB)
- **GC overhead**: ~5-10MB
- **Temporary variables**: ~2-5MB

#### Total RAM Estimate

**Current configuration (2 URLs, with display)**:
- OS + Python base: 65-110MB
- Application code: 5-10MB
- Threading (3 threads): 9-21MB
- SQLite: 2-7MB
- Libraries (requests + PyYAML): 7-13MB
- Display libraries (SSD1306 + Pillow + RPi.GPIO): 7-14MB
- Display framebuffer: < 1MB
- Runtime overhead: 10-21MB
- **TOTAL**: ~103-189MB ✅

**Target configuration (10 URLs, with display)**:
- Same base: 103-189MB
- More data in memory (more checks): +5-10MB
- **TOTAL**: ~108-199MB ✅

#### RAM Utilization

| Configuration | RAM Used | Available (Lite) | Utilization |
|---------------|----------|------------------|-------------|
| 2 URLs + display | 103-189MB | ~448MB | 23-42% ✅ |
| 10 URLs + display | 108-199MB | ~448MB | 24-44% ✅ |
| 10 URLs + display (gpu_mem=16) | 108-199MB | ~496MB | 22-40% ✅ |

**RAM Conclusion**: ✅ **Fully Supported** - With Raspberry Pi OS Lite, there is abundant headroom. Even at 10 URLs with display, utilization stays below 50%. No memory concerns.

---

### 3. Storage (SD Card - Slow I/O)

#### Disk Operations

**Writes**:
- **INSERT per check**: 1 write per check
  - With 10 URLs every 60s: ~600 checks/hour = ~600 writes/hour
  - With WAL mode: ~2-4 I/O operations per INSERT (WAL + periodic checkpoint)
- **Periodic cleanup** (7-day retention):
  - DELETE queries: ~1 operation per day/week
- **WAL checkpoint**:
  - Automatic or manual: ~1 per minute or after N operations
  - ~1-2MB of data written per checkpoint

**Reads**:
- **API queries**: ~1-5 reads per request
  - With low traffic: negligible
- **Indexes**: Primarily in memory (small dataset)

#### Write Estimate

**Per hour** (10 URLs):
- Checks: 600/hour × 2-4 I/O ops = ~1,200-2,400 I/O operations/hour
- WAL checkpoints: ~60 checkpoints/hour × ~0.1-0.2MB = ~6-12MB/hour
- **Total**: ~1,200-2,400 I/O ops + ~6-12MB written/hour

**Per day** (10 URLs):
- Checks: ~14,400 checks/day × ~100 bytes/check = ~1.44MB/day in data
- WAL checkpoints: ~144-288MB/day (periodic writes)
- **DB growth**: ~1.44MB/day (with 7-day retention = ~10MB maximum)

**Storage Conclusion**: ✅ **Supported** - Write volume is moderate even at 10 URLs. WAL mode reduces random writes (better for SD). 7-day retention limits DB size. With class 10 SD card, performance is adequate.

---

### 4. Network (Ethernet 10/100)

#### Network Traffic

**Monitoring Outbound**:
- **HTTP GET requests**:
  - 10 URLs × 60s interval = ~600 requests/hour
  - Request size: ~200-500 bytes
  - Typical response size: ~10-100KB per website
  - **Total**: ~6-60MB/hour inbound, ~120-300KB/hour outbound

**API Inbound** (if used):
- Low traffic: < 1 request/s
  - Request: ~200 bytes
  - JSON response: ~500 bytes - 2KB
  - **Total**: < 1MB/hour

**Network Conclusion**: ✅ **Supported** - Traffic is minimal even at 10 URLs. Ethernet 10/100 (up to 12.5MB/s) is far above current usage (< 65MB/hour = ~18KB/s). No network saturation risk.

---

### 5. I2C Bus (Display Communication)

#### I2C Operations

**Display Updates**:
- **Frequency**: 1-2 FPS (0.5-1 second between frames)
- **Frame size**: 1024 bytes (128×64 monochrome, 1 bit per pixel)
- **I2C transfer**: ~1-2ms per frame at 100kHz standard mode
- **I2C frequency**: 100kHz standard (not 400kHz fast mode for reliability)

**Bus Load**:
- With 1-2 FPS: ~2-4 transfers/second = ~0.2-0.4% bus utilization
- I2C bus can handle up to 100kHz = ~12.5KB/s
- Current usage: ~1-2KB/s (< 0.02% utilization)

**I2C Conclusion**: ✅ **Supported** - I2C bus load is negligible. 100kHz standard mode is reliable and sufficient.

---

## Scalability Analysis

### Recommended Limits

- **Max URLs**: 10 URLs ✅
- **Min interval**: ≥ 30 seconds (60s recommended)
- **Max timeout**: ≤ 10 seconds
- **Hardware**: OLED display + LEDs + buzzer + button

### Load Scenarios

| Scenario | URLs | Interval | CPU Est. | RAM Est. | RAM % | Status |
|----------|------|----------|----------|----------|-------|--------|
| **Current** | 2 | 60s | 13-32% | 103-189MB | 23-42% | ✅ **OK** |
| **Moderate** | 5 | 60s | 14-36% | 106-194MB | 24-43% | ✅ **OK** |
| **Target** | 10 | 60s | 15-44% | 108-199MB | 24-44% | ✅ **OK** |
| **Maximum** | 10 | 30s | 17-54% | 108-199MB | 24-44% | ⚠️ **Limit** |

---

## Identified Risks

### 1. ⚠️ Memory Leaks (Medium Risk)

**Problem**: If memory leaks exist in code (especially in threads or DB connections), RAM can grow unbounded.

**Mitigation**:
- Extended memory testing (24+ hours)
- Monitor RAM usage in production
- Proper resource cleanup (DB connections, threads)

### 2. ✅ RAM Pressure (Low Risk)

**Problem**: Originally a concern when assuming ~256MB available RAM (desktop mode).

**Resolution**: Raspberry Pi OS Lite with `gpu_mem=16` provides **~496MB available RAM**. Current usage (~108-199MB) is only ~22-40% utilization. Comfortable headroom exists.

### 3. ⚠️ SD Card Wear (Medium-Low Risk)

**Problem**: Excessive writes can degrade SD card prematurely.

**Mitigation**:
- WAL mode already implemented (reduces random writes)
- 7-day retention limits DB growth
- Checkpoint configured appropriately
- Consider higher quality SD card (class 10 or higher)

### 4. ⚠️ CPU Spikes on Timeouts (Low Risk)

**Problem**: If multiple URLs timeout simultaneously, CPU spikes may occur.

**Mitigation**:
- Staggered intervals to avoid bursts
- Reasonable timeouts (10s is adequate)
- Limited thread pool if concurrent checks are implemented

### 5. ✅ Network Saturation (Very Low Risk)

**Problem**: Network traffic is minimal, no risk.

### 6. ✅ I2C Bus Saturation (Very Low Risk)

**Problem**: I2C bus usage is negligible (< 0.02% utilization).

---

## Recommendations

### Optimal Configuration for Pi 1B+ with Lite

1. **OS**: Raspberry Pi OS Lite (no desktop)
2. **GPU Memory**: Set `gpu_mem=16` in `/boot/config.txt`
3. **URLs**: Up to 10 URLs supported ✅
4. **Intervals**: 60s recommended (30s minimum)
5. **Timeouts**: 10s maximum
6. **Retention**: 7 days is reasonable
7. **Hardware**: OLED display + LEDs + buzzer + button

### Production Monitoring

1. **RAM Usage**: Monitor RAM trend (detect leaks)
2. **CPU Usage**: Verify average stays < 50%
3. **DB Size**: Verify it doesn't grow unbounded
4. **SD Card Health**: Monitor I/O errors if possible
5. **I2C Errors**: Monitor display communication failures

### Future Optimizations (if needed)

1. **Staggered Start**: Offset URL check start times to avoid bursts
2. **Batch Inserts**: Group multiple INSERTs if frequency increases
3. **Query Optimization**: Use appropriate indexes (already implemented)
4. **Connection Pooling**: Limit DB connections if threads are scaled
5. **Display optimization**: Pre-render fonts, update only on data change

---

## General Conclusion

### ✅ **Raspberry Pi 1B+ with Lite FULLY supports the target load (10 URLs with OLED display)**

**Justification**:
- **CPU**: Estimated load 15-44% at 10 URLs with display ✅
- **RAM**: Estimated usage 108-199MB (~22-40% of available) ✅
- **Storage**: Moderate I/O, WAL mode reduces writes ✅
- **Network**: Minimal traffic, no saturation risk ✅
- **I2C**: Negligible bus load ✅

**Key Insight**: The original analysis assumed ~256MB available RAM (desktop mode). With Raspberry Pi OS Lite and `gpu_mem=16`, **~496MB is available** - nearly double. This provides comfortable headroom for all features including the OLED display.

---

## Next Steps

1. ✅ Implement monitor loop and API server
2. ⚠️ Extended memory testing (24+ hours)
3. ⚠️ **Validate on real hardware before production**
4. ⚠️ Configure `gpu_mem=16` on target Pi
5. ⚠️ Test display at 1-2 FPS refresh rate
