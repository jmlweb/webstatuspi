"""JavaScript core functionality for the dashboard.

This module contains the main dashboard rendering, API fetching,
modal handling, and event listeners.
"""

JS_CORE = """
        function renderCard(url) {
            const statusClass = url.is_up ? 'up' : 'down';
            const cardClass = url.is_up ? '' : ' down';
            const statusCode = url.status_code !== null ? url.status_code : '---';
            const errorHtml = url.error
                ? `<div class="error-text" title="${escapeHtml(url.error)}" role="alert">${escapeHtml(url.error)}</div>`
                : '';

            const latencyPercent = getLatencyPercent(url.response_time_ms);
            const latencyClass = getLatencyClass(url.response_time_ms);
            const latencyState = getLatencyState(url.response_time_ms);
            const uptimePercent = url.uptime_24h !== null ? url.uptime_24h : 0;
            const uptimeColor = getUptimeColor(url.uptime_24h);

            // Build stats row HTML (avg/min/max response times)
            const hasResponseStats = url.avg_response_time_24h !== null ||
                                     url.min_response_time_24h !== null ||
                                     url.max_response_time_24h !== null;
            const statsRowHtml = hasResponseStats ? `
                <div class="stats-row" aria-hidden="true">
                    <div class="mini-stat">
                        <div class="mini-stat-label">Avg</div>
                        <div class="mini-stat-value">${formatResponseTime(url.avg_response_time_24h)}</div>
                    </div>
                    <div class="mini-stat">
                        <div class="mini-stat-label">Min</div>
                        <div class="mini-stat-value">${formatResponseTime(url.min_response_time_24h)}</div>
                    </div>
                    <div class="mini-stat">
                        <div class="mini-stat-label">Max</div>
                        <div class="mini-stat-value">${formatResponseTime(url.max_response_time_24h)}</div>
                    </div>
                    <div class="mini-stat">
                        <div class="mini-stat-label">\\u03C3</div>
                        <div class="mini-stat-value">${formatResponseTime(url.stddev_response_time_24h)}</div>
                    </div>
                </div>
            ` : '';

            // Build warning banner for consecutive failures
            const warningHtml = url.consecutive_failures > 0 ? `
                <div class="warning-banner" role="alert">
                    ${url.consecutive_failures} consecutive failure${url.consecutive_failures > 1 ? 's' : ''}
                    ${url.last_downtime ? ' \\u2022 Last down: ' + formatRelativeTime(url.last_downtime) : ''}
                </div>
            ` : '';

            // Build footer with last check and content length
            const contentInfo = url.content_length !== null ? ` \\u2022 Size: ${formatBytes(url.content_length)}` : '';

            const statusText = url.is_up ? 'online' : 'offline';
            const latencyText = url.response_time_ms ? url.response_time_ms + ' milliseconds' : 'unknown';
            const uptimeText = url.uptime_24h !== null ? url.uptime_24h.toFixed(1) + ' percent' : 'unknown';
            const ariaLabel = `${escapeHtml(url.name)}, ${statusText}, ` +
                `latency ${latencyText}, uptime ${uptimeText}. Press Enter or Space to view history.`;

            return `
                <article class="card${cardClass}"
                    tabindex="0"
                    role="button"
                    aria-label="${ariaLabel}"
                    data-url-name="${escapeHtml(url.name)}"
>
                    <div class="card-anchor" aria-hidden="true"></div>
                    <header class="card-header">
                        <span class="status-indicator ${statusClass}" aria-hidden="true"></span>
                        <h2 class="card-name" title="${escapeHtml(url.name)}">${escapeHtml(url.name)}</h2>
                    </header>
                    <div class="card-metrics" aria-hidden="true">
                        <div class="metric">
                            <div class="metric-label" data-tooltip="HTTP status code. 2xx=success, 4xx=client error, 5xx=server error">Status</div>
                            <div class="metric-value">${statusCode}</div>
                        </div>
                        <div class="metric" data-latency-state="${latencyState}">
                            <div class="metric-label" data-tooltip="Response time. Green: <200ms, Yellow: 500-1000ms, Red: >1000ms">Latency</div>
                            <div class="metric-value">${formatResponseTimeWithWarning(url.response_time_ms)}</div>
                            <div class="progress-bar" role="progressbar"
                                aria-valuenow="${url.response_time_ms || 0}"
                                aria-valuemin="0" aria-valuemax="2000"
                                aria-label="Latency indicator"
                                data-tooltip="Scale: 0-2000ms maps to 0-100%">
                                <div class="progress-fill ${latencyClass}" data-width="${latencyPercent}"></div>
                            </div>
                        </div>
                        <div class="metric">
                            <div class="metric-label" data-tooltip="Percentage of successful checks in the last 24 hours">Uptime</div>
                            <div class="metric-value">${formatUptime(url.uptime_24h)}</div>
                            <div class="progress-bar" role="progressbar"
                                aria-valuenow="${uptimePercent}"
                                aria-valuemin="0" aria-valuemax="100"
                                aria-label="Uptime indicator"
                                data-tooltip="100% = all checks successful">
                                <div class="progress-fill"
                                    data-width="${uptimePercent}"
                                    data-color="${uptimeColor}"></div>
                            </div>
                        </div>
                        <div class="metric metric-empty"></div>
                    </div>
                    ${statsRowHtml}
                    ${warningHtml}
                    ${errorHtml}
                    <footer class="card-footer">
                        LAST_SCAN: ${formatTime(url.last_check)}${contentInfo}
                    </footer>
                </article>
            `;
        }

        function renderDashboard(data, showPulse = true) {
            // Batch DOM updates to reduce reflows
            requestAnimationFrame(function() {
                const countUp = document.getElementById('countUp');
                const countDown = document.getElementById('countDown');
                countUp.textContent = '[' + data.summary.up + '] ONLINE';
                countDown.textContent = '[' + data.summary.down + '] OFFLINE';
                // Update aria-labels with current counts
                countUp.setAttribute('aria-label', data.summary.up + ' services online');
                countDown.setAttribute('aria-label', data.summary.down + ' services offline');
                countUp.classList.toggle('count-dimmed', data.summary.up === 0);
                countDown.classList.toggle('count-dimmed', data.summary.down === 0);
                const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false });
                document.getElementById('updatedTime').textContent = '// SYNC: ' + timeStr;

                const container = document.getElementById('cardsContainer');
                if (data.urls.length === 0) {
                    container.innerHTML = '<div class="no-data" role="status">NO_TARGETS_CONFIGURED</div>';
                } else {
                    // Use DocumentFragment for better performance on large updates
                    const fragment = document.createDocumentFragment();
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = data.urls.map(renderCard).join('');
                    while (tempDiv.firstChild) {
                        fragment.appendChild(tempDiv.firstChild);
                    }
                    container.innerHTML = '';
                    container.appendChild(fragment);

                    // Apply CSS custom properties from data attributes
                    document.querySelectorAll('.progress-fill').forEach(bar => {
                        const width = bar.dataset.width;
                        const color = bar.dataset.color;
                        if (width) bar.style.setProperty('--progress-width', width + '%');
                        if (color) bar.style.setProperty('--progress-color', color);
                        // Trigger pulse effect on latency bars
                        if (showPulse) {
                            bar.classList.add('pulse');
                            setTimeout(() => bar.classList.remove('pulse'), 200);
                        }
                    });
                }
            });
        }

        async function fetchStatus() {
            const liveDot = document.getElementById('liveDot');
            liveDot.classList.add('updating');
            isUpdating = true;

            try {
                const response = await fetchWithTimeout('/status');
                if (!response.ok) throw new Error('Failed to fetch status');

                const data = await response.json();
                renderDashboard(data);

                // Check if response came from Service Worker cache
                const fromCache = response.headers.get('X-From-Cache') === 'true';
                const banner = document.getElementById('offlineBanner');

                if (fromCache) {
                    // Server down but we have cached data - show reconnecting message
                    if (banner) {
                        banner.textContent = '⚡ RECONNECTING - Showing cached data';
                        banner.hidden = false;
                    }
                } else {
                    // Server responded successfully - hide offline banner
                    if (banner) {
                        banner.textContent = '⚠ OFFLINE MODE - Showing cached data';
                        banner.hidden = true;
                    }
                }
            } catch (error) {
                console.error('Error fetching status:', error);
                document.getElementById('updatedTime').textContent = '// ERROR: CONNECTION_FAILED';
                // Server not responding - show offline banner
                const banner = document.getElementById('offlineBanner');
                if (banner) {
                    banner.textContent = '⚠ OFFLINE MODE - Showing cached data';
                    banner.hidden = false;
                }
            } finally {
                liveDot.classList.remove('updating');
                isUpdating = false;
            }
        }

        function initializeDashboard() {
            // Use DOMContentLoaded if available, otherwise execute immediately
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() {
                    initializeDashboardData();
                });
            } else {
                // DOM already loaded
                initializeDashboardData();
            }
        }

        // Tab visibility tracking for adaptive polling
        let pollInterval = null;
        let isTabActive = !document.hidden;

        function startPolling() {
            if (pollInterval) clearInterval(pollInterval);

            // Poll every 10s when active, 50s when inactive
            const interval = isTabActive ? POLL_INTERVAL : POLL_INTERVAL * 5;

            pollInterval = setInterval(() => {
                if (isTabActive) {
                    fetchStatus();
                }
            }, interval);
        }

        // Detect tab visibility changes
        document.addEventListener('visibilitychange', () => {
            isTabActive = !document.hidden;

            if (isTabActive) {
                // Tab became active - fetch immediately and restart polling
                fetchStatus();
                startPolling();
            } else {
                // Tab became inactive - slow down polling
                startPolling();
            }
        });

        function initializeDashboardData() {
            // Enable Google Fonts stylesheet (CSP-compliant async loading)
            const fontLink = document.getElementById('googleFonts');
            if (fontLink) {
                fontLink.media = 'all';
            }

            // Try to use server-provided initial data
            const initialDataEl = document.getElementById('initialData');
            if (initialDataEl) {
                try {
                    const data = JSON.parse(initialDataEl.textContent);
                    if (data && data.urls && data.summary) {
                        renderDashboard(data, false);  // No pulse on initial render
                    } else {
                        fetchStatus();  // Fallback if data is invalid
                    }
                } catch (e) {
                    console.warn('Failed to parse initial data, fetching from API:', e);
                    fetchStatus();  // Fallback on parse error
                }
            } else {
                fetchStatus();  // Fallback if no initial data element
            }

            // Start adaptive polling
            startPolling();
        }

        initializeDashboard();

        // Modal functionality
        let currentUrlData = null;
        let lastFocusedElement = null;  // Track element that opened modal
        const inFlightRequests = new Map();  // Track pending requests to deduplicate
        const renderedCharts = new Set();  // Track which charts have been rendered

        // Focus trap helper - gets all focusable elements in a container
        function getFocusableElements(container) {
            return container.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
        }

        // Focus trap handler
        function trapFocus(event, modal) {
            const focusable = getFocusableElements(modal.querySelector('.modal-content, .reset-modal-content'));
            const firstFocusable = focusable[0];
            const lastFocusable = focusable[focusable.length - 1];

            if (event.key === 'Tab') {
                if (event.shiftKey) {
                    // Shift + Tab
                    if (document.activeElement === firstFocusable) {
                        event.preventDefault();
                        lastFocusable.focus();
                    }
                } else {
                    // Tab
                    if (document.activeElement === lastFocusable) {
                        event.preventDefault();
                        firstFocusable.focus();
                    }
                }
            }
        }

        function openModal(urlName) {
            const modal = document.getElementById('historyModal');
            const modalTitle = document.getElementById('modalTitle');
            const tableBody = document.getElementById('historyTableBody');

            // Save currently focused element to restore later
            lastFocusedElement = document.activeElement;

            modalTitle.textContent = urlName;
            tableBody.innerHTML =
                '<tr><td colspan="5" class="history-loading" role="status">LOADING_HISTORY...</td></tr>';

            // Reset summary values
            document.getElementById('modalStatus').textContent = '---';
            document.getElementById('modalStatus').className = 'modal-stat-value';
            document.getElementById('modalCode').textContent = '---';
            document.getElementById('modalLatency').textContent = '---';
            document.getElementById('modalUptime').textContent = '---';

            // Reset URL bar and additional details
            document.getElementById('modalUrl').textContent = '---';
            document.getElementById('modalServer').textContent = '---';
            document.getElementById('modalStatusText').textContent = '---';
            document.getElementById('modalP50').textContent = '---';
            document.getElementById('modalP95').textContent = '---';
            document.getElementById('modalP99').textContent = '---';
            document.getElementById('modalMin').textContent = '---';
            document.getElementById('modalMax').textContent = '---';
            document.getElementById('modalAvg').textContent = '---';
            document.getElementById('modalStddev').textContent = '---';
            document.getElementById('modalLastDown').textContent = '---';

            modal.classList.add('active');

            // Reset to graphs tab when opening modal
            switchTab('graphs');

            // Set up focus trap
            modal.addEventListener('keydown', historyModalKeyHandler);

            // Focus the close button after a brief delay for animation
            setTimeout(() => {
                const closeBtn = modal.querySelector('.modal-close');
                if (closeBtn) closeBtn.focus();
            }, 100);

            fetchHistory(urlName);
        }

        function historyModalKeyHandler(event) {
            trapFocus(event, document.getElementById('historyModal'));
        }

        function closeModal() {
            const modal = document.getElementById('historyModal');
            modal.classList.remove('active');

            // Remove focus trap handler
            modal.removeEventListener('keydown', historyModalKeyHandler);

            // Clear rendered charts state so they render fresh on next open
            renderedCharts.clear();

            // Return focus to the element that opened the modal
            if (lastFocusedElement) {
                lastFocusedElement.focus();
                lastFocusedElement = null;
            }
        }

        async function fetchHistory(urlName) {
            // Return existing promise if request already in flight
            if (inFlightRequests.has(urlName)) {
                return inFlightRequests.get(urlName);
            }

            // Create promise for this request
            const requestPromise = (async () => {
                // Show loading state in charts
                clearAllCharts();

                try {
                    // Fetch current status for summary
                    const statusResponse = await fetchWithTimeout('/status/' + encodeURIComponent(urlName));
                    if (statusResponse.ok) {
                        const statusData = await statusResponse.json();
                        updateModalSummary(statusData);
                    }

                    // Fetch history
                    const historyResponse = await fetchWithTimeout('/history/' + encodeURIComponent(urlName));
                    if (!historyResponse.ok) {
                        throw new Error('Failed to fetch history');
                    }

                    const data = await historyResponse.json();
                    currentUrlData = data;  // Store data for lazy chart rendering
                    renderHistoryTable(data.checks);

                    // Only render charts if Analytics tab is active
                    const graphsTab = document.getElementById('graphsTab');
                    if (graphsTab && graphsTab.classList.contains('active')) {
                        renderAllChartsLazy(data.checks);
                    }
                } catch (error) {
                    console.error('Error fetching history:', error);
                    document.getElementById('historyTableBody').innerHTML =
                        '<tr><td colspan="5" class="history-empty">// ERROR: FAILED_TO_LOAD_HISTORY</td></tr>';
                    // Show error state in charts
                    ['responseTimeChart', 'uptimeChart', 'statusCodeChart', 'latencyHistogram'].forEach(id => {
                        showEmptyState(document.getElementById(id), 'Error loading data');
                    });
                } finally {
                    // Clean up tracking when request completes
                    inFlightRequests.delete(urlName);
                }
            })();

            // Track the promise
            inFlightRequests.set(urlName, requestPromise);
            return requestPromise;
        }

        function updateModalSummary(data) {
            const statusEl = document.getElementById('modalStatus');
            const statusText = data.is_up ? 'ONLINE' : 'OFFLINE';
            statusEl.textContent = statusText;
            statusEl.className = 'modal-stat-value ' + (data.is_up ? 'up' : 'down');
            statusEl.setAttribute('aria-label', 'Current status: ' + statusText);

            const codeEl = document.getElementById('modalCode');
            const codeText = data.status_code !== null ? data.status_code : '---';
            codeEl.textContent = codeText;
            codeEl.setAttribute('aria-label', 'HTTP status code: ' + codeText);

            const latencyEl = document.getElementById('modalLatency');
            const latencyText = formatResponseTime(data.response_time_ms);
            latencyEl.textContent = latencyText;
            latencyEl.setAttribute('aria-label', 'Response latency: ' + latencyText);

            const uptimeEl = document.getElementById('modalUptime');
            const uptimeText = formatUptime(data.uptime_24h);
            uptimeEl.textContent = uptimeText;
            uptimeEl.setAttribute('aria-label', '24 hour uptime: ' + uptimeText);

            // URL info bar
            document.getElementById('modalUrl').textContent = data.url || '---';
            document.getElementById('modalServer').textContent = data.server_header || '---';
            const statusCodeText = data.status_code !== null ? data.status_code + ' ' + (data.status_text || 'OK') : '---';
            document.getElementById('modalStatusText').textContent = statusCodeText;

            // Percentiles
            document.getElementById('modalP50').textContent = formatResponseTime(data.p50_response_time_24h);
            document.getElementById('modalP95').textContent = formatResponseTime(data.p95_response_time_24h);
            document.getElementById('modalP99').textContent = formatResponseTime(data.p99_response_time_24h);

            // Range
            document.getElementById('modalMin').textContent = formatResponseTime(data.min_response_time_24h);
            document.getElementById('modalMax').textContent = formatResponseTime(data.max_response_time_24h);
            document.getElementById('modalAvg').textContent = formatResponseTime(data.avg_response_time_24h);
            document.getElementById('modalStddev').textContent = formatResponseTime(data.stddev_response_time_24h);

            // Last down
            const lastDownEl = document.getElementById('modalLastDown');
            if (data.last_down) {
                lastDownEl.textContent = formatRelativeTime(data.last_down);
            } else {
                lastDownEl.textContent = 'Never';
            }
        }

        function renderHistoryTable(checks) {
            const tableBody = document.getElementById('historyTableBody');

            if (!checks || checks.length === 0) {
                tableBody.innerHTML =
                    '<tr><td colspan="5" class="history-empty" role="status">// NO_HISTORY_DATA</td></tr>';
                return;
            }

            tableBody.innerHTML = checks.map(check => {
                const statusClass = check.is_up ? 'up' : 'down';
                const statusText = check.is_up ? 'UP' : 'DOWN';
                const code = check.status_code !== null ? check.status_code : '---';
                const latency = check.response_time_ms ? check.response_time_ms + 'ms' : '---';
                const errorTitle = escapeHtml(check.error);
                const error = check.error
                    ? `<span class="error-cell" title="${errorTitle}">${errorTitle}</span>`
                    : '---';
                const time = formatDateTime(check.checked_at);

                return `
                    <tr>
                        <td>${time}</td>
                        <td class="status-cell">
                            <span class="status-dot ${statusClass}" aria-hidden="true"></span>
                            <span class="sr-only">Status: </span>${statusText}
                        </td>
                        <td><span class="sr-only">HTTP Code: </span>${code}</td>
                        <td><span class="sr-only">Latency: </span>${latency}</td>
                        <td>${error}</td>
                    </tr>
                `;
            }).join('');
        }

        let resetModalTrigger = null;  // Track element that opened reset modal

        function resetModalKeyHandler(event) {
            trapFocus(event, document.getElementById('resetModal'));
        }

        function showResetModal() {
            const resetModal = document.getElementById('resetModal');

            // Save the trigger element
            resetModalTrigger = document.activeElement;

            resetModal.classList.add('active');
            document.getElementById('confirmResetBtn').disabled = false;

            // Set up focus trap
            resetModal.addEventListener('keydown', resetModalKeyHandler);

            // Focus the cancel button (safer default)
            setTimeout(() => {
                const cancelBtn = resetModal.querySelector('.reset-button-cancel');
                if (cancelBtn) cancelBtn.focus();
            }, 100);
        }

        function cancelReset() {
            const resetModal = document.getElementById('resetModal');
            resetModal.classList.remove('active');

            // Remove focus trap handler
            resetModal.removeEventListener('keydown', resetModalKeyHandler);

            // Return focus to trigger element
            if (resetModalTrigger) {
                resetModalTrigger.focus();
                resetModalTrigger = null;
            }
        }

        function confirmReset() {
            const confirmBtn = document.getElementById('confirmResetBtn');
            confirmBtn.disabled = true;
            confirmBtn.textContent = 'RESETTING...';

            // Announce to screen readers
            const announcement = document.createElement('div');
            announcement.setAttribute('role', 'status');
            announcement.setAttribute('aria-live', 'polite');
            announcement.className = 'sr-only';
            announcement.textContent = 'Resetting data, please wait...';
            document.body.appendChild(announcement);

            fetchWithTimeout('/reset', { method: 'DELETE' })
                .then(async response => {
                    const data = await response.json();
                    if (response.ok) {
                        return data;
                    }
                    // Use server error message if available
                    throw new Error(data.error || 'Failed to reset data');
                })
                .then(data => {
                    announcement.textContent = 'Data reset successfully.';
                    setTimeout(() => announcement.remove(), 1000);
                    cancelReset();
                    confirmBtn.textContent = 'Confirm Reset';
                    // Refresh the dashboard data
                    fetchStatus();
                })
                .catch(error => {
                    announcement.textContent = 'Reset failed: ' + error.message;
                    setTimeout(() => announcement.remove(), 1000);
                    cancelReset();
                    confirmBtn.textContent = 'Confirm Reset';
                    alert(error.message);
                });
        }

        // Close modal on backdrop click
        document.getElementById('historyModal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal();
            }
        });

        document.getElementById('resetModal').addEventListener('click', function(e) {
            if (e.target === this) {
                cancelReset();
            }
        });

        // Close modal on ESC key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeModal();
                cancelReset();
            }
        });

        // Tab switching functionality
        function switchTab(tabName) {
            const graphsTab = document.getElementById('graphsTab');
            const historyTab = document.getElementById('historyTab');
            const graphsTabBtn = document.getElementById('graphsTabBtn');
            const historyTabBtn = document.getElementById('historyTabBtn');

            if (tabName === 'graphs') {
                graphsTab.classList.add('active');
                historyTab.classList.remove('active');
                graphsTabBtn.classList.add('active');
                historyTabBtn.classList.remove('active');
                graphsTabBtn.setAttribute('aria-selected', 'true');
                historyTabBtn.setAttribute('aria-selected', 'false');

                // Lazy render charts when switching to Analytics tab
                if (currentUrlData && renderedCharts.size === 0) {
                    renderAllChartsLazy(currentUrlData.checks);
                }
            } else {
                graphsTab.classList.remove('active');
                historyTab.classList.add('active');
                graphsTabBtn.classList.remove('active');
                historyTabBtn.classList.add('active');
                graphsTabBtn.setAttribute('aria-selected', 'false');
                historyTabBtn.setAttribute('aria-selected', 'true');
            }
        }

        // Button event listeners (CSP-compliant, no inline handlers)
        document.getElementById('resetDataBtn').addEventListener('click', showResetModal);
        document.getElementById('historyModalClose').addEventListener('click', closeModal);
        document.getElementById('resetModalClose').addEventListener('click', cancelReset);
        document.getElementById('resetCancelBtn').addEventListener('click', cancelReset);
        document.getElementById('confirmResetBtn').addEventListener('click', confirmReset);

        // Tab button listeners
        document.getElementById('graphsTabBtn').addEventListener('click', () => switchTab('graphs'));
        document.getElementById('historyTabBtn').addEventListener('click', () => switchTab('history'));

        // Arrow key navigation for tabs (WCAG 2.1.1)
        document.querySelector('.modal-tabs').addEventListener('keydown', function(e) {
            const tabs = ['graphsTabBtn', 'historyTabBtn'];
            const currentIndex = tabs.indexOf(document.activeElement.id);
            if (currentIndex === -1) return;

            let newIndex = -1;
            if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                e.preventDefault();
                newIndex = currentIndex === 0 ? tabs.length - 1 : currentIndex - 1;
            } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                e.preventDefault();
                newIndex = currentIndex === tabs.length - 1 ? 0 : currentIndex + 1;
            } else if (e.key === 'Home') {
                e.preventDefault();
                newIndex = 0;
            } else if (e.key === 'End') {
                e.preventDefault();
                newIndex = tabs.length - 1;
            }

            if (newIndex !== -1) {
                const newTab = document.getElementById(tabs[newIndex]);
                newTab.focus();
                switchTab(newIndex === 0 ? 'graphs' : 'history');
            }
        });

        // Card click/keyboard event delegation (for dynamically created cards)
        document.getElementById('cardsContainer').addEventListener('click', function(e) {
            const card = e.target.closest('.card');
            if (card) {
                const urlName = card.dataset.urlName;
                if (urlName) openModal(urlName);
            }
        });

        document.getElementById('cardsContainer').addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                const card = e.target.closest('.card');
                if (card) {
                    e.preventDefault();
                    const urlName = card.dataset.urlName;
                    if (urlName) openModal(urlName);
                }
            }
        });

        // Prefetch API endpoints on card hover (mouseenter uses event capturing for better performance)
        document.getElementById('cardsContainer').addEventListener('mouseenter', function(e) {
            const card = e.target.closest('.card');
            if (card && card.dataset.urlName) {
                addPrefetchHint(card.dataset.urlName);
            }
        }, true);

        // Touch support for mobile devices
        document.getElementById('cardsContainer').addEventListener('touchstart', function(e) {
            const card = e.target.closest('.card');
            if (card && card.dataset.urlName) {
                addPrefetchHint(card.dataset.urlName);
            }
        }, { passive: true });

        // ============================================
        // Resource Hints for API Prefetching
        // ============================================
        function addPrefetchHint(urlName) {
            const encoded = encodeURIComponent(urlName);
            // Check if hints already exist for this URL
            if (document.querySelector(`link[href*="${encoded}"]`)) return;

            // Prefetch status endpoint
            const statusLink = document.createElement('link');
            statusLink.rel = 'prefetch';
            statusLink.href = '/status/' + encoded;
            statusLink.as = 'fetch';
            document.head.appendChild(statusLink);

            // Prefetch history endpoint
            const historyLink = document.createElement('link');
            historyLink.rel = 'prefetch';
            historyLink.href = '/history/' + encoded;
            historyLink.as = 'fetch';
            document.head.appendChild(historyLink);
        }

        // ============================================
        // Lazy Chart Rendering
        // ============================================
        function renderAllChartsLazy(checks) {
            // Render charts incrementally using requestAnimationFrame
            const charts = [
                { id: 'responseTimeChart', fn: renderResponseTimeChart },
                { id: 'uptimeChart', fn: renderUptimeChart },
                { id: 'statusCodeChart', fn: renderStatusCodeChart },
                { id: 'latencyHistogram', fn: renderLatencyHistogram }
            ];

            let chartIndex = 0;

            function renderNext() {
                if (chartIndex >= charts.length) return;

                requestAnimationFrame(() => {
                    const chart = charts[chartIndex];
                    const container = document.getElementById(chart.id);
                    if (container && !renderedCharts.has(chart.id)) {
                        // Reverse for chronological order (for time-based charts)
                        const chronologicalChecks = chart.id === 'responseTimeChart' || chart.id === 'uptimeChart'
                            ? [...checks].reverse()
                            : checks;
                        chart.fn(container, chronologicalChecks);
                        renderedCharts.add(chart.id);
                    }
                    chartIndex++;
                    renderNext();
                });
            }

            renderNext();
        }

        // ============================================
        // Service Worker Registration
        // ============================================
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/sw.js')
                    .then(registration => {
                        console.log('[PWA] Service Worker registered:', registration.scope);
                        // Check for updates periodically
                        setInterval(() => {
                            registration.update();
                        }, 60000); // Check every minute
                    })
                    .catch(error => {
                        console.error('[PWA] Service Worker registration failed:', error);
                    });
            });
        }

        // ============================================
        // PWA Install Button (inspired by pwa-install)
        // ============================================
        let deferredInstallPrompt = null;
        const installBtn = document.getElementById('installBtn');

        // Check if already installed (standalone mode)
        function isAppInstalled() {
            return window.matchMedia('(display-mode: standalone)').matches ||
                   window.navigator.standalone === true;
        }

        // Hide install button if already installed
        if (isAppInstalled()) {
            console.log('[PWA] App is already installed');
        }

        // Capture the install prompt event
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredInstallPrompt = e;
            console.log('[PWA] Install prompt captured');

            // Show the install button
            if (installBtn && !isAppInstalled()) {
                installBtn.hidden = false;
            }
        });

        // Handle install button click
        if (installBtn) {
            installBtn.addEventListener('click', async () => {
                if (!deferredInstallPrompt) {
                    console.log('[PWA] No install prompt available');
                    return;
                }

                // Show the browser install prompt
                deferredInstallPrompt.prompt();

                // Wait for user response
                const { outcome } = await deferredInstallPrompt.userChoice;
                console.log('[PWA] User choice:', outcome);

                if (outcome === 'accepted') {
                    installBtn.hidden = true;
                }

                // Clear the deferred prompt
                deferredInstallPrompt = null;
            });
        }

        // Listen for successful installation
        window.addEventListener('appinstalled', () => {
            console.log('[PWA] App installed successfully');
            if (installBtn) {
                installBtn.hidden = true;
            }
            deferredInstallPrompt = null;
        });

        // ============================================
        // Offline Detection (uses hidden attribute, CSP-safe)
        // ============================================
        const offlineBanner = document.getElementById('offlineBanner');

        function showOfflineBanner() {
            if (offlineBanner) offlineBanner.hidden = false;
        }

        function hideOfflineBanner() {
            if (offlineBanner) offlineBanner.hidden = true;
        }

        window.addEventListener('online', function() {
            hideOfflineBanner();
            fetchStatus();
        });
        window.addEventListener('offline', showOfflineBanner);

        // Check initial status
        if (!navigator.onLine) {
            showOfflineBanner();
        }
"""
