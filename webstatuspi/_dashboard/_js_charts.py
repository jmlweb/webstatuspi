"""JavaScript chart rendering functions for the dashboard.

This module contains SVG chart utilities and all chart rendering functions.
"""

JS_CHARTS = """
        // ============================================
        // SVG Chart Utilities
        // ============================================

        const SVG_NS = 'http://www.w3.org/2000/svg';

        function createSvgElement(tag, attrs = {}) {
            const el = document.createElementNS(SVG_NS, tag);
            for (const [key, value] of Object.entries(attrs)) {
                el.setAttribute(key, value);
            }
            return el;
        }

        function clearContainer(container) {
            container.innerHTML = '';
        }

        function showEmptyState(container, message) {
            clearContainer(container);
            const div = document.createElement('div');
            div.className = 'graph-empty';
            div.textContent = message;
            container.appendChild(div);
        }

        // Tooltip management
        let activeTooltip = null;

        function createTooltip(container) {
            let tooltip = container.querySelector('.chart-tooltip');
            if (!tooltip) {
                tooltip = document.createElement('div');
                tooltip.className = 'chart-tooltip';
                container.appendChild(tooltip);
            }
            return tooltip;
        }

        function showTooltip(tooltip, x, y, content, containerRect) {
            tooltip.innerHTML = content;
            tooltip.classList.add('visible');

            // Position tooltip, avoiding overflow
            const tooltipRect = tooltip.getBoundingClientRect();
            let left = x + 10;
            let top = y - 10;

            if (left + tooltipRect.width > containerRect.width) {
                left = x - tooltipRect.width - 10;
            }
            if (top < 0) {
                top = y + 20;
            }

            tooltip.style.left = left + 'px';
            tooltip.style.top = top + 'px';
            activeTooltip = tooltip;
        }

        function hideTooltip(tooltip) {
            tooltip.classList.remove('visible');
            activeTooltip = null;
        }

        // ============================================
        // Response Time Line Chart
        // ============================================

        function renderResponseTimeChart(container, checks) {
            clearContainer(container);

            // Filter checks with valid response times
            const validChecks = checks.filter(c => c.response_time_ms !== null && c.response_time_ms !== undefined);

            if (validChecks.length === 0) {
                showEmptyState(container, 'No response time data');
                return;
            }

            const rect = container.getBoundingClientRect();
            const width = rect.width || 300;
            const height = rect.height || 100;
            const padding = { top: 15, right: 10, bottom: 20, left: 40 };
            const chartWidth = width - padding.left - padding.right;
            const chartHeight = height - padding.top - padding.bottom;

            // Sample data if too many points
            const data = validChecks.length > 60
                ? validChecks.filter((_, i) => i % Math.ceil(validChecks.length / 60) === 0)
                : validChecks;

            // Calculate scales
            const times = data.map(c => new Date(c.checked_at).getTime());
            const values = data.map(c => c.response_time_ms);
            const minTime = Math.min(...times);
            const maxTime = Math.max(...times);
            const maxValue = Math.max(...values, 100); // At least 100ms scale

            const xScale = (t) => padding.left + ((t - minTime) / (maxTime - minTime || 1)) * chartWidth;
            const yScale = (v) => padding.top + chartHeight - (v / maxValue) * chartHeight;

            // Create SVG
            const svg = createSvgElement('svg', {
                viewBox: `0 0 ${width} ${height}`,
                preserveAspectRatio: 'xMidYMid meet'
            });

            // Draw grid lines
            const gridLines = [0, 0.25, 0.5, 0.75, 1].map(pct => {
                const y = padding.top + chartHeight * (1 - pct);
                return createSvgElement('line', {
                    x1: padding.left, y1: y,
                    x2: width - padding.right, y2: y,
                    class: 'chart-grid'
                });
            });
            gridLines.forEach(line => svg.appendChild(line));

            // Draw axes
            const xAxis = createSvgElement('line', {
                x1: padding.left, y1: height - padding.bottom,
                x2: width - padding.right, y2: height - padding.bottom,
                class: 'chart-axis'
            });
            const yAxis = createSvgElement('line', {
                x1: padding.left, y1: padding.top,
                x2: padding.left, y2: height - padding.bottom,
                class: 'chart-axis'
            });
            svg.appendChild(xAxis);
            svg.appendChild(yAxis);

            // Y-axis labels
            [0, 0.5, 1].forEach(pct => {
                const value = Math.round(maxValue * pct);
                const y = padding.top + chartHeight * (1 - pct);
                const label = createSvgElement('text', {
                    x: padding.left - 5,
                    y: y + 3,
                    class: 'chart-label',
                    'text-anchor': 'end'
                });
                label.textContent = value >= 1000 ? (value / 1000).toFixed(1) + 's' : value + 'ms';
                svg.appendChild(label);
            });

            // Build line path
            if (data.length > 1) {
                const pathData = data.map((c, i) => {
                    const x = xScale(new Date(c.checked_at).getTime());
                    const y = yScale(c.response_time_ms);
                    return (i === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1);
                }).join(' ');

                const path = createSvgElement('path', {
                    d: pathData,
                    class: 'chart-line'
                });
                svg.appendChild(path);
            }

            // Create tooltip and hover elements
            const tooltip = createTooltip(container);

            // Vertical hover line
            const hoverLine = createSvgElement('line', {
                x1: 0, y1: padding.top,
                x2: 0, y2: height - padding.bottom,
                class: 'chart-hover-line'
            });
            hoverLine.style.display = 'none';
            svg.appendChild(hoverLine);

            // Hover point
            const hoverPoint = createSvgElement('circle', {
                cx: 0, cy: 0, r: 4,
                class: 'chart-hover-point'
            });
            hoverPoint.style.display = 'none';
            svg.appendChild(hoverPoint);

            // Invisible overlay for mouse events
            const overlay = createSvgElement('rect', {
                x: padding.left,
                y: padding.top,
                width: chartWidth,
                height: chartHeight,
                fill: 'transparent',
                class: 'chart-overlay'
            });

            overlay.addEventListener('mousemove', (e) => {
                const svgRect = svg.getBoundingClientRect();
                const mouseX = (e.clientX - svgRect.left) * (width / svgRect.width);

                // Find closest data point
                let closestIdx = 0;
                let closestDist = Infinity;
                data.forEach((c, i) => {
                    const x = xScale(new Date(c.checked_at).getTime());
                    const dist = Math.abs(x - mouseX);
                    if (dist < closestDist) {
                        closestDist = dist;
                        closestIdx = i;
                    }
                });

                const closest = data[closestIdx];
                const x = xScale(new Date(closest.checked_at).getTime());
                const y = yScale(closest.response_time_ms);

                // Update hover line
                hoverLine.setAttribute('x1', x);
                hoverLine.setAttribute('x2', x);
                hoverLine.style.display = 'block';

                // Update hover point
                hoverPoint.setAttribute('cx', x);
                hoverPoint.setAttribute('cy', y);
                hoverPoint.style.display = 'block';

                // Show tooltip
                const content = `<div class="chart-tooltip-time">${formatChartTime(closest.checked_at)}</div>
                    <div class="chart-tooltip-value">${closest.response_time_ms}ms</div>`;
                showTooltip(tooltip, e.offsetX, e.offsetY, content, rect);
            });

            overlay.addEventListener('mouseleave', () => {
                hoverLine.style.display = 'none';
                hoverPoint.style.display = 'none';
                hideTooltip(tooltip);
            });

            svg.appendChild(overlay);

            container.appendChild(svg);
        }

        // ============================================
        // Uptime Timeline Chart
        // ============================================

        function renderUptimeChart(container, checks) {
            clearContainer(container);

            if (!checks || checks.length === 0) {
                showEmptyState(container, 'No uptime data');
                return;
            }

            const rect = container.getBoundingClientRect();
            const width = rect.width || 300;
            const height = rect.height || 80;
            const padding = { top: 10, right: 10, bottom: 15, left: 40 };
            const chartWidth = width - padding.left - padding.right;
            const chartHeight = height - padding.top - padding.bottom;

            // Sort by time
            const sortedChecks = [...checks].sort((a, b) =>
                new Date(a.checked_at) - new Date(b.checked_at)
            );

            // Calculate time range
            const times = sortedChecks.map(c => new Date(c.checked_at).getTime());
            const minTime = Math.min(...times);
            const maxTime = Math.max(...times);
            const timeRange = maxTime - minTime || 1;

            const xScale = (t) => padding.left + ((t - minTime) / timeRange) * chartWidth;

            // Create SVG
            const svg = createSvgElement('svg', {
                viewBox: `0 0 ${width} ${height}`,
                preserveAspectRatio: 'xMidYMid meet'
            });

            // Draw axis
            const xAxis = createSvgElement('line', {
                x1: padding.left, y1: height - padding.bottom,
                x2: width - padding.right, y2: height - padding.bottom,
                class: 'chart-axis'
            });
            svg.appendChild(xAxis);

            // Labels
            const upLabel = createSvgElement('text', {
                x: padding.left - 5,
                y: padding.top + chartHeight * 0.25 + 3,
                class: 'chart-label',
                'text-anchor': 'end'
            });
            upLabel.textContent = 'UP';
            svg.appendChild(upLabel);

            const downLabel = createSvgElement('text', {
                x: padding.left - 5,
                y: padding.top + chartHeight * 0.75 + 3,
                class: 'chart-label',
                'text-anchor': 'end'
            });
            downLabel.textContent = 'DOWN';
            svg.appendChild(downLabel);

            // Draw status blocks
            const blockHeight = chartHeight * 0.4;
            const tooltip = createTooltip(container);

            sortedChecks.forEach((check, i) => {
                const currentTime = new Date(check.checked_at).getTime();
                const nextTime = i < sortedChecks.length - 1
                    ? new Date(sortedChecks[i + 1].checked_at).getTime()
                    : currentTime + (timeRange / sortedChecks.length);

                const x = xScale(currentTime);
                const blockWidth = Math.max(2, xScale(nextTime) - x);
                const y = check.is_up
                    ? padding.top + (chartHeight - blockHeight) * 0.25
                    : padding.top + (chartHeight - blockHeight) * 0.75 + blockHeight * 0.5;

                const rect2 = createSvgElement('rect', {
                    x: x,
                    y: y,
                    width: blockWidth,
                    height: blockHeight,
                    class: check.is_up ? 'chart-area chart-area-up' : 'chart-area chart-area-down',
                    rx: 1
                });

                rect2.addEventListener('mouseenter', (e) => {
                    const status = check.is_up ? '<span style="color:var(--green)">UP</span>' : '<span style="color:var(--red)">DOWN</span>';
                    const content = `<div class="chart-tooltip-time">${formatChartTime(check.checked_at)}</div>
                        <div>${status}</div>`;
                    showTooltip(tooltip, e.offsetX, e.offsetY, content, rect);
                });
                rect2.addEventListener('mouseleave', () => hideTooltip(tooltip));

                svg.appendChild(rect2);
            });

            container.appendChild(svg);
        }

        // ============================================
        // Status Code Distribution Bar Chart
        // ============================================

        function renderStatusCodeChart(container, checks) {
            clearContainer(container);

            // Group by status code
            const codeCounts = {};
            checks.forEach(c => {
                if (c.status_code !== null && c.status_code !== undefined) {
                    codeCounts[c.status_code] = (codeCounts[c.status_code] || 0) + 1;
                }
            });

            const codes = Object.keys(codeCounts).sort((a, b) => a - b);

            if (codes.length === 0) {
                showEmptyState(container, 'No status codes');
                return;
            }

            const rect = container.getBoundingClientRect();
            const width = rect.width || 200;
            const height = rect.height || 120;
            const padding = { top: 15, right: 10, bottom: 25, left: 30 };
            const chartWidth = width - padding.left - padding.right;
            const chartHeight = height - padding.top - padding.bottom;

            const maxCount = Math.max(...Object.values(codeCounts));
            const barWidth = Math.min(30, (chartWidth / codes.length) - 4);
            const barGap = (chartWidth - barWidth * codes.length) / (codes.length + 1);

            // Create SVG
            const svg = createSvgElement('svg', {
                viewBox: `0 0 ${width} ${height}`,
                preserveAspectRatio: 'xMidYMid meet'
            });

            // Draw axis
            const xAxis = createSvgElement('line', {
                x1: padding.left, y1: height - padding.bottom,
                x2: width - padding.right, y2: height - padding.bottom,
                class: 'chart-axis'
            });
            svg.appendChild(xAxis);

            // Draw bars
            const tooltip = createTooltip(container);

            codes.forEach((code, i) => {
                const count = codeCounts[code];
                const barHeight = (count / maxCount) * chartHeight;
                const x = padding.left + barGap + i * (barWidth + barGap);
                const y = height - padding.bottom - barHeight;

                // Determine color class
                let colorClass = 'chart-bar-other';
                const codeNum = parseInt(code);
                if (codeNum >= 200 && codeNum < 300) colorClass = 'chart-bar-2xx';
                else if (codeNum >= 300 && codeNum < 400) colorClass = 'chart-bar-3xx';
                else if (codeNum >= 400 && codeNum < 500) colorClass = 'chart-bar-4xx';
                else if (codeNum >= 500) colorClass = 'chart-bar-5xx';

                const bar = createSvgElement('rect', {
                    x: x, y: y,
                    width: barWidth,
                    height: barHeight,
                    class: 'chart-bar ' + colorClass,
                    rx: 1
                });

                bar.addEventListener('mouseenter', (e) => {
                    const pct = ((count / checks.length) * 100).toFixed(1);
                    const content = `<div class="chart-tooltip-value">${code}</div>
                        <div>${count} checks (${pct}%)</div>`;
                    showTooltip(tooltip, e.offsetX, e.offsetY, content, rect);
                });
                bar.addEventListener('mouseleave', () => hideTooltip(tooltip));

                svg.appendChild(bar);

                // Code label below bar
                const labelClass = colorClass.replace('chart-bar-', 'chart-label-');
                const label = createSvgElement('text', {
                    x: x + barWidth / 2,
                    y: height - padding.bottom + 12,
                    class: 'chart-label ' + labelClass,
                    'text-anchor': 'middle'
                });
                label.textContent = code;
                svg.appendChild(label);

                // Count label above bar
                if (barHeight > 15) {
                    const countLabel = createSvgElement('text', {
                        x: x + barWidth / 2,
                        y: y + 10,
                        class: 'chart-value-label',
                        'text-anchor': 'middle'
                    });
                    countLabel.textContent = count;
                    svg.appendChild(countLabel);
                }
            });

            container.appendChild(svg);
        }

        // ============================================
        // Latency Distribution Histogram
        // ============================================

        function renderLatencyHistogram(container, checks) {
            clearContainer(container);

            // Filter valid response times
            const validTimes = checks
                .filter(c => c.response_time_ms !== null && c.response_time_ms !== undefined)
                .map(c => c.response_time_ms);

            if (validTimes.length === 0) {
                showEmptyState(container, 'No latency data');
                return;
            }

            // Define buckets
            const buckets = [
                { label: '<100', min: 0, max: 100, class: 'chart-bar-fast' },
                { label: '100-300', min: 100, max: 300, class: 'chart-bar-medium' },
                { label: '300-500', min: 300, max: 500, class: 'chart-bar-slow' },
                { label: '500-1k', min: 500, max: 1000, class: 'chart-bar-veryslow' },
                { label: '>1k', min: 1000, max: Infinity, class: 'chart-bar-timeout' }
            ];

            // Count values in each bucket
            buckets.forEach(b => {
                b.count = validTimes.filter(t => t >= b.min && t < b.max).length;
            });

            // Filter out empty buckets
            const nonEmptyBuckets = buckets.filter(b => b.count > 0);

            if (nonEmptyBuckets.length === 0) {
                showEmptyState(container, 'No latency data');
                return;
            }

            const rect = container.getBoundingClientRect();
            const width = rect.width || 200;
            const height = rect.height || 120;
            const padding = { top: 15, right: 10, bottom: 25, left: 30 };
            const chartWidth = width - padding.left - padding.right;
            const chartHeight = height - padding.top - padding.bottom;

            const maxCount = Math.max(...nonEmptyBuckets.map(b => b.count));
            const barWidth = Math.min(35, (chartWidth / nonEmptyBuckets.length) - 4);
            const barGap = (chartWidth - barWidth * nonEmptyBuckets.length) / (nonEmptyBuckets.length + 1);

            // Create SVG
            const svg = createSvgElement('svg', {
                viewBox: `0 0 ${width} ${height}`,
                preserveAspectRatio: 'xMidYMid meet'
            });

            // Draw axis
            const xAxis = createSvgElement('line', {
                x1: padding.left, y1: height - padding.bottom,
                x2: width - padding.right, y2: height - padding.bottom,
                class: 'chart-axis'
            });
            svg.appendChild(xAxis);

            // Draw bars
            const tooltip = createTooltip(container);

            nonEmptyBuckets.forEach((bucket, i) => {
                const barHeight = (bucket.count / maxCount) * chartHeight;
                const x = padding.left + barGap + i * (barWidth + barGap);
                const y = height - padding.bottom - barHeight;

                const bar = createSvgElement('rect', {
                    x: x, y: y,
                    width: barWidth,
                    height: barHeight,
                    class: 'chart-bar ' + bucket.class,
                    rx: 1
                });

                bar.addEventListener('mouseenter', (e) => {
                    const pct = ((bucket.count / validTimes.length) * 100).toFixed(1);
                    const content = `<div class="chart-tooltip-value">${bucket.label}ms</div>
                        <div>${bucket.count} checks (${pct}%)</div>`;
                    showTooltip(tooltip, e.offsetX, e.offsetY, content, rect);
                });
                bar.addEventListener('mouseleave', () => hideTooltip(tooltip));

                svg.appendChild(bar);

                // Label below bar
                const labelClass = bucket.class.replace('chart-bar-', 'chart-label-');
                const label = createSvgElement('text', {
                    x: x + barWidth / 2,
                    y: height - padding.bottom + 12,
                    class: 'chart-label ' + labelClass,
                    'text-anchor': 'middle'
                });
                label.textContent = bucket.label;
                svg.appendChild(label);

                // Count label above bar
                if (barHeight > 15) {
                    const countLabel = createSvgElement('text', {
                        x: x + barWidth / 2,
                        y: y + 10,
                        class: 'chart-value-label',
                        'text-anchor': 'middle'
                    });
                    countLabel.textContent = bucket.count;
                    svg.appendChild(countLabel);
                }
            });

            container.appendChild(svg);
        }

        // ============================================
        // Render All Charts
        // ============================================

        function renderAllCharts(checks) {
            // Reverse to get chronological order (newest first from API)
            const chronologicalChecks = [...checks].reverse();

            renderResponseTimeChart(
                document.getElementById('responseTimeChart'),
                chronologicalChecks
            );
            renderUptimeChart(
                document.getElementById('uptimeChart'),
                chronologicalChecks
            );
            renderStatusCodeChart(
                document.getElementById('statusCodeChart'),
                checks
            );
            renderLatencyHistogram(
                document.getElementById('latencyHistogram'),
                checks
            );
        }

        function clearAllCharts() {
            ['responseTimeChart', 'uptimeChart', 'statusCodeChart', 'latencyHistogram'].forEach(id => {
                const container = document.getElementById(id);
                if (container) {
                    container.innerHTML = '<div class="graph-empty">Loading...</div>';
                }
            });
        }
"""
