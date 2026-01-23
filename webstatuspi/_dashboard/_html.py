"""HTML template for the dashboard.

This module contains the HTML structure with placeholders for CSS and JavaScript.
"""


def build_html(css: str, js_utils: str, js_charts: str, js_core: str) -> str:
    """Build the complete HTML dashboard from its components.

    Args:
        css: CSS styles string
        js_utils: JavaScript utility functions string
        js_charts: JavaScript chart functions string
        js_core: JavaScript core functionality string

    Returns:
        Complete HTML dashboard string
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- PWA meta tags -->
    <meta name="theme-color" content="#00fff9">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="WebStatusPi">
    <title>WebStatusPi // SYSTEM MONITOR</title>
    <!-- PWA manifest and icons -->
    <link rel="manifest" href="/manifest.json">
    <link rel="apple-touch-icon" href="/icon-192.png">
    <!-- Preconnect to Google Fonts for faster font loading -->
    <link rel="preconnect" href="https://fonts.googleapis.com" crossorigin>
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <!-- Load fonts asynchronously to avoid blocking render -->
    <link rel="stylesheet" media="print" id="googleFonts"
        href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap">
    <noscript><link rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap"></noscript>
    <style nonce="__CSP_NONCE__">{css}
    </style>
</head>
<body>
    <a href="#cardsContainer" class="skip-link">Skip to main content</a>
    <!-- Offline banner (hidden by default, shown when offline) -->
    <div id="offlineBanner" class="offline-banner" role="alert" hidden>
        // OFFLINE MODE - Showing cached data
    </div>
    <div class="scanline-overlay" aria-hidden="true"></div>
    <header role="banner">
        <h1>&lt;WebStatusPi/&gt;</h1>
        <div class="live-indicator" role="status" aria-live="polite" aria-label="Live feed status">
            <span class="live-dot" id="liveDot" aria-hidden="true"></span>
            <span id="liveStatusText">// LIVE FEED [10 sec]</span>
        </div>
    </header>
    <nav class="summary-bar" aria-label="Status summary">
        <div class="summary-counts" role="status" aria-live="polite" aria-atomic="true">
            <span class="count-up" id="countUp" aria-label="0 services online">[0] ONLINE</span>
            <span class="count-down" id="countDown" aria-label="0 services offline">[0] OFFLINE</span>
        </div>
        <div>
            <span class="updated-time" id="updatedTime" role="status" aria-live="polite">// INITIALIZING...</span>
            <button class="reset-button" id="resetDataBtn"
                aria-label="Reset all monitoring data" type="button">// RESET DATA</button>
        </div>
    </nav>
    <main id="cardsContainer" role="main" aria-label="Service status cards">
        <div class="no-data" role="status">LOADING_SYSTEM_STATUS...</div>
    </main>

    <!-- History Modal -->
    <div class="modal" id="historyModal" role="dialog" aria-modal="true"
        aria-labelledby="modalTitle" aria-describedby="modalDescription">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title" id="modalTitle">URL_NAME</h2>
                <button class="modal-close" id="historyModalClose"
                    aria-label="Close history modal" type="button">&times;</button>
            </div>
            <p id="modalDescription" class="sr-only">Service status history and metrics</p>
            <!-- URL info bar -->
            <div class="modal-url-bar" id="modalUrlBar">
                <span class="modal-url-info">
                    <span class="modal-url-label">URL:</span>
                    <span class="modal-url-value" id="modalUrl">---</span>
                </span>
                <span class="modal-server-info">
                    <span class="modal-server-label">SERVER:</span>
                    <span class="modal-server-value" id="modalServer">---</span>
                    <span class="modal-status-label">STATUS:</span>
                    <span class="modal-status-value" id="modalStatusText">---</span>
                </span>
            </div>
            <section class="modal-summary" id="modalSummary" aria-label="Current status summary">
                <div class="modal-stat">
                    <div class="modal-stat-value" id="modalStatus" aria-label="Current status">---</div>
                    <div class="modal-stat-label" id="modalStatusLabel">Status</div>
                </div>
                <div class="modal-stat">
                    <div class="modal-stat-value" id="modalCode" aria-label="HTTP status code">---</div>
                    <div class="modal-stat-label">Code</div>
                </div>
                <div class="modal-stat">
                    <div class="modal-stat-value" id="modalLatency" aria-label="Response latency">---</div>
                    <div class="modal-stat-label">Latency</div>
                </div>
                <div class="modal-stat">
                    <div class="modal-stat-value" id="modalUptime" aria-label="24 hour uptime percentage">---</div>
                    <div class="modal-stat-label">Uptime 24h</div>
                </div>
                <div class="modal-stat">
                    <div class="modal-stat-value" id="modalLastDown" aria-label="Last downtime">---</div>
                    <div class="modal-stat-label">Last Down</div>
                </div>
            </section>
            <!-- Additional Details (PERCENTILES and RANGE) - Direct Display -->
            <div class="modal-additional-details">
                <div class="modal-metrics-container">
                    <div class="modal-metrics-group">
                        <span class="modal-metrics-title">PERCENTILES</span>
                        <div class="modal-metrics-row">
                            <span class="modal-metric-item">
                                <span class="modal-metric-label">P50:</span>
                                <span class="modal-metric-value" id="modalP50">---</span>
                            </span>
                            <span class="modal-metric-item">
                                <span class="modal-metric-label">P95:</span>
                                <span class="modal-metric-value" id="modalP95">---</span>
                            </span>
                            <span class="modal-metric-item">
                                <span class="modal-metric-label">P99:</span>
                                <span class="modal-metric-value" id="modalP99">---</span>
                            </span>
                        </div>
                    </div>
                    <div class="modal-metrics-group">
                        <span class="modal-metrics-title">RANGE</span>
                        <div class="modal-metrics-row">
                            <span class="modal-metric-item">
                                <span class="modal-metric-label">MIN:</span>
                                <span class="modal-metric-value modal-value-green" id="modalMin">---</span>
                            </span>
                            <span class="modal-metric-item">
                                <span class="modal-metric-label">MAX:</span>
                                <span class="modal-metric-value modal-value-orange" id="modalMax">---</span>
                            </span>
                            <span class="modal-metric-item">
                                <span class="modal-metric-label">AVG:</span>
                                <span class="modal-metric-value" id="modalAvg">---</span>
                            </span>
                            <span class="modal-metric-item">
                                <span class="modal-metric-label">&#x3c3;:</span>
                                <span class="modal-metric-value" id="modalStddev">---</span>
                            </span>
                        </div>
                    </div>
                </div>
            </div>
            <section class="modal-body" aria-label="Service analytics and history">
                <!-- Tabs Navigation -->
                <div class="modal-tabs" role="tablist">
                    <button class="modal-tab active" role="tab" aria-selected="true" aria-controls="graphsTab" id="graphsTabBtn">Analytics</button>
                    <button class="modal-tab" role="tab" aria-selected="false" aria-controls="historyTab" id="historyTabBtn">Raw History</button>
                </div>
                <!-- Graphs Tab Content -->
                <div class="modal-tab-content active" id="graphsTab" role="tabpanel" aria-labelledby="graphsTabBtn">
                    <div class="graphs-grid" id="graphsGrid" aria-label="Service metrics charts">
                        <div class="graph-panel graph-panel-wide">
                            <h3 class="graph-title">Response Time</h3>
                            <div class="graph-container" id="responseTimeChart" aria-label="Response time over last 24 hours"></div>
                        </div>
                        <div class="graph-panel graph-panel-wide">
                            <h3 class="graph-title">Uptime Timeline</h3>
                            <div class="graph-container" id="uptimeChart" aria-label="Uptime and downtime periods"></div>
                        </div>
                        <div class="graph-panel">
                            <h3 class="graph-title">Status Codes</h3>
                            <div class="graph-container" id="statusCodeChart" aria-label="HTTP status code distribution"></div>
                        </div>
                        <div class="graph-panel">
                            <h3 class="graph-title">Latency Distribution</h3>
                            <div class="graph-container" id="latencyHistogram" aria-label="Response time distribution"></div>
                        </div>
                    </div>
                </div>
                <!-- History Tab Content -->
                <div class="modal-tab-content" id="historyTab" role="tabpanel" aria-labelledby="historyTabBtn">
                    <table class="history-table" aria-label="Service check history">
                        <thead>
                            <tr>
                                <th scope="col">Time</th>
                                <th scope="col">Status</th>
                                <th scope="col">Code</th>
                                <th scope="col">Latency</th>
                                <th scope="col">Error</th>
                            </tr>
                        </thead>
                        <tbody id="historyTableBody">
                            <tr><td colspan="5" class="history-loading" role="status">LOADING_HISTORY...</td></tr>
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    </div>

    <!-- Reset Confirmation Modal -->
    <div class="modal" id="resetModal" role="alertdialog" aria-modal="true"
        aria-labelledby="resetModalTitle" aria-describedby="resetWarningText">
        <div class="reset-modal-content">
            <div class="reset-modal-header">
                <h2 class="reset-modal-title" id="resetModalTitle">Confirm Reset</h2>
                <button class="modal-close" id="resetModalClose"
                    aria-label="Cancel and close" type="button">&times;</button>
            </div>
            <div class="reset-modal-body">
                <div class="reset-warning" id="resetWarningText" role="alert">
                    This will delete all monitoring data. This action cannot be undone.
                </div>
                <p>Are you sure you want to reset all check records from the database?</p>
            </div>
            <div class="reset-modal-actions">
                <button class="reset-button-cancel" id="resetCancelBtn" type="button">Cancel</button>
                <button class="reset-button-confirm" id="confirmResetBtn" type="button">Confirm Reset</button>
            </div>
        </div>
    </div>

    <script id="initialData" type="application/json">__INITIAL_DATA__</script>
    <script nonce="__CSP_NONCE__">{js_utils}{js_charts}{js_core}
    </script>
</body>
</html>"""
