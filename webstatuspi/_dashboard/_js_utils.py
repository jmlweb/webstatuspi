"""JavaScript utility functions for the dashboard.

This module contains formatting and helper functions used across the dashboard.
"""

JS_UTILS = """
        const POLL_INTERVAL = 10000;
        const FETCH_TIMEOUT_MS = 60000;  // 60 second timeout for slow RPi hardware
        let isUpdating = false;

        // Helper function to fetch with timeout
        async function fetchWithTimeout(url, options = {}) {
            const controller = new AbortController();
            const timeout = setTimeout(() => {
                controller.abort(new DOMException('Request timed out after ' + FETCH_TIMEOUT_MS + 'ms', 'TimeoutError'));
            }, FETCH_TIMEOUT_MS);
            try {
                // Don't pass signal if options already has one (avoid conflict)
                const fetchOptions = options.signal
                    ? options
                    : { ...options, signal: controller.signal };
                const response = await fetch(url, fetchOptions);
                return response;
            } finally {
                clearTimeout(timeout);
            }
        }

        function formatTime(isoString) {
            if (!isoString) return '---';
            const date = new Date(isoString);
            if (isNaN(date.getTime())) return '---';
            return date.toLocaleTimeString(navigator.language);
        }

        function formatResponseTime(ms) {
            if (ms === null || ms === undefined || ms === 0) return '---';
            return ms + 'ms';
        }

        function formatResponseTimeWithWarning(ms) {
            if (ms === null || ms === undefined || ms === 0) return '---';
            let prefix = '';
            if (ms >= 1000) {
                prefix = '<span class="latency-warning-prefix danger" aria-label="High latency warning">[!]</span>';
            } else if (ms >= 500) {
                prefix = '<span class="latency-warning-prefix warning" aria-label="Elevated latency warning">[!]</span>';
            }
            return prefix + ms + 'ms';
        }

        function formatUptime(uptime) {
            if (uptime === null || uptime === undefined) return '---';
            return uptime.toFixed(1) + '%';
        }

        function formatBytes(bytes) {
            if (bytes === null || bytes === undefined) return '---';
            if (bytes < 1024) return bytes + 'B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB';
            return (bytes / (1024 * 1024)).toFixed(1) + 'MB';
        }

        function formatRelativeTime(isoString) {
            if (!isoString) return '---';
            const date = new Date(isoString);
            const now = new Date();
            const diffMs = now - date;
            const diffSec = Math.floor(diffMs / 1000);
            const diffMin = Math.floor(diffSec / 60);
            const diffHr = Math.floor(diffMin / 60);
            const diffDay = Math.floor(diffHr / 24);

            if (diffSec < 60) return diffSec + 's ago';
            if (diffMin < 60) return diffMin + 'm ago';
            if (diffHr < 24) return diffHr + 'h ago';
            return diffDay + 'd ago';
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function getLatencyClass(ms) {
            if (ms === null || ms === undefined || ms === 0) return '';
            if (ms < 200) return 'success';
            if (ms < 500) return '';
            if (ms < 1000) return 'warning';
            return 'danger';
        }

        function getLatencyPercent(ms) {
            if (ms === null || ms === undefined || ms === 0) return 0;
            // Scale: 0-2000ms maps to 0-100%
            return Math.min(100, (ms / 2000) * 100);
        }

        function getUptimeColor(uptime) {
            if (uptime === null || uptime === undefined) return 'var(--cyan)';

            // Color stops: 100%=green, 95%=cyan, 80%=yellow, 60%=orange, <40%=red
            const stops = [
                { pct: 100, r: 0,   g: 255, b: 102 },  // green
                { pct: 95,  r: 0,   g: 255, b: 249 },  // cyan
                { pct: 80,  r: 240, g: 255, b: 0   },  // yellow
                { pct: 60,  r: 255, g: 136, b: 0   },  // orange
                { pct: 40,  r: 255, g: 0,   b: 64  },  // red
            ];

            // Clamp uptime to 0-100
            uptime = Math.max(0, Math.min(100, uptime));

            // Find the two stops to interpolate between
            for (let i = 0; i < stops.length - 1; i++) {
                if (uptime >= stops[i + 1].pct) {
                    const upper = stops[i];
                    const lower = stops[i + 1];
                    const range = upper.pct - lower.pct;
                    const t = (uptime - lower.pct) / range;

                    const r = Math.round(lower.r + (upper.r - lower.r) * t);
                    const g = Math.round(lower.g + (upper.g - lower.g) * t);
                    const b = Math.round(lower.b + (upper.b - lower.b) * t);

                    return `rgb(${r}, ${g}, ${b})`;
                }
            }

            // Below lowest stop = red
            return 'rgb(255, 0, 64)';
        }

        function formatDateTime(isoString) {
            const date = new Date(isoString);
            return date.toLocaleString(navigator.language, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }

        function formatChartTime(isoString) {
            const date = new Date(isoString);
            return date.toLocaleTimeString(navigator.language, {
                hour: '2-digit',
                minute: '2-digit'
            });
        }
"""
