"""HTML dashboard for the monitoring web interface.

This module contains the embedded HTML/CSS/JS dashboard served at the root endpoint.
The dashboard is static HTML that fetches data dynamically via JavaScript from /status.

Separated from api.py for better maintainability while keeping zero dependencies.
"""

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebStatusPi // SYSTEM MONITOR</title>
    <!-- Preconnect to Google Fonts for faster font loading -->
    <link rel="preconnect" href="https://fonts.googleapis.com" crossorigin>
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <!-- Load fonts asynchronously to avoid blocking render -->
    <link rel="stylesheet" media="print" onload="this.media='all'"
        href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap">
    <noscript><link rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap"></noscript>
    <style nonce="__CSP_NONCE__">

        :root {
            --bg-dark: #0a0a0f;
            --bg-panel: #12121a;
            --cyan: #00fff9;
            --magenta: #ff00ff;
            --yellow: #f0ff00;
            --orange: #ff8800;
            --green: #00ff66;
            --red: #ff0040;
            --text: #e0e0e0;
            --text-dim: #606080;
            --border: #2a2a3a;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            /* Use fallback fonts first to prevent FOIT (Flash of Invisible Text) */
            /* JetBrains Mono will swap in when loaded due to display=swap parameter */
            font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
            background: var(--bg-dark);
            color: var(--text);
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }

        /* Scanline effect */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: repeating-linear-gradient(
                0deg,
                rgba(0, 0, 0, 0.15) 0px,
                rgba(0, 0, 0, 0.15) 1px,
                transparent 1px,
                transparent 3px
            );
            pointer-events: none;
            z-index: 1000;
            opacity: 0.04;
        }


        /* Horizontal scan line animation - with long pause between cycles */
        @keyframes scanline {
            0% { top: -5%; opacity: 1; }
            25% { top: 105%; opacity: 1; }
            25.1% { opacity: 0; }
            99.9% { opacity: 0; top: -5%; }
            100% { top: -5%; opacity: 1; }
        }

        .scanline-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(
                180deg,
                transparent 0%,
                rgba(0, 255, 249, 0.02) 50%,
                transparent 100%
            );
            animation: scanline 32s linear infinite;
            pointer-events: none;
            z-index: 1001;
        }

        /* CRT flicker - subtle, with long pause between cycles */
        @keyframes flicker {
            0%, 97% { opacity: 1; }
            98% { opacity: 0.97; }
            99%, 100% { opacity: 1; }
        }

        body { animation: flicker 36s infinite; }

        /* Offline/Error flicker animation */
        @keyframes errorFlicker {
            0%, 100% { opacity: 1; }
            10% { opacity: 0.8; }
            20% { opacity: 1; }
            30% { opacity: 0.9; }
            50% { opacity: 1; }
            70% { opacity: 0.85; }
            80% { opacity: 1; }
        }

        header {
            background: var(--bg-panel);
            padding: 1rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--cyan);
            box-shadow: 0 0 20px rgba(0, 255, 249, 0.15);
        }

        header h1 {
            font-size: 1.1rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.2em;
            color: var(--cyan);
            text-shadow: 0 0 10px var(--cyan), 0 0 20px var(--cyan);
        }

        .live-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-dim);
            text-shadow: 0 0 4px rgba(96, 96, 128, 0.5);
        }

        .live-dot {
            width: 8px;
            height: 8px;
            background: var(--green);
            box-shadow: 0 0 10px var(--green), 0 0 20px var(--green);
            clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%);
            animation: pulse 1.5s infinite;
        }

        .live-dot.updating {
            background: var(--yellow);
            box-shadow: 0 0 10px var(--yellow), 0 0 20px var(--yellow);
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.6; transform: scale(0.9); }
        }

        .summary-bar {
            background: var(--bg-panel);
            padding: 0.75rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .summary-counts { display: flex; gap: 1.5rem; }

        .count-up {
            color: var(--green);
            text-shadow: 0 0 8px var(--green), 0 0 16px var(--green);
        }

        .count-down {
            color: var(--red);
            text-shadow: 0 0 8px var(--red), 0 0 16px var(--red);
        }

        .count-dimmed {
            opacity: 0.3;
            text-shadow: none;
        }

        .updated-time {
            color: var(--text-dim);
            text-shadow: 0 0 4px rgba(96, 96, 128, 0.4);
        }

        main {
            padding: 2rem 2.5rem;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 420px));
            gap: 1.5rem;
            max-width: 1000px;
            margin: 0 auto;
            min-height: calc(100vh - 120px);
            align-content: center;
            justify-content: center;
        }

        /* Reserve space for cards to prevent layout shift */
        #cardsContainer {
            min-height: 200px;
            contain: layout style paint;
        }

        /* When 4+ cards, limit to 2 columns for better balance */
        @media (min-width: 1000px) {
            main {
                grid-template-columns: repeat(2, minmax(300px, 420px));
            }
        }

        .card {
            background: var(--bg-panel);
            border: 1px solid var(--border);
            padding: 1.25rem 1.5rem;
            position: relative;
            clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px));
            transition: all 0.3s ease;
            box-shadow: 0 0 8px rgba(0, 255, 249, 0.1);
            /* Reserve space to prevent layout shift */
            min-height: 200px;
            contain: layout style;
        }

        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(0, 255, 249, 0.03) 0%, transparent 50%);
            pointer-events: none;
        }

        /* Corner anchor indicator - top right */
        .card::after {
            content: '';
            position: absolute;
            top: 4px;
            right: 16px;
            width: 4px;
            height: 4px;
            background: var(--cyan);
            box-shadow: 0 0 6px var(--cyan), 0 0 12px var(--cyan);
        }

        .card:hover {
            border-color: var(--cyan);
            box-shadow: 0 0 15px rgba(0, 255, 249, 0.25),
                0 0 30px rgba(0, 255, 249, 0.15),
                inset 0 0 20px rgba(0, 255, 249, 0.05);
        }

        .card.down {
            border-color: var(--red);
            box-shadow: 0 0 8px rgba(255, 0, 64, 0.2);
            animation: errorFlicker 3s infinite;
        }

        .card.down::after {
            background: var(--red);
            box-shadow: 0 0 6px var(--red), 0 0 12px var(--red);
        }

        .card.down:hover {
            box-shadow: 0 0 15px rgba(255, 0, 64, 0.35),
                0 0 30px rgba(255, 0, 64, 0.2),
                inset 0 0 20px rgba(255, 0, 64, 0.05);
        }

        /* Bottom left anchor indicator */
        .card-anchor {
            position: absolute;
            bottom: 4px;
            left: 16px;
            width: 4px;
            height: 4px;
            background: var(--text-dim);
            opacity: 0.5;
        }

        .card-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--border);
        }

        .status-indicator {
            width: 12px;
            height: 12px;
            position: relative;
        }

        .status-indicator::before {
            content: '';
            position: absolute;
            width: 100%;
            height: 100%;
            clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%);
        }

        .status-indicator.up::before {
            background: var(--green);
            box-shadow: 0 0 10px var(--green);
        }

        .status-indicator.down::before {
            background: var(--red);
            box-shadow: 0 0 10px var(--red);
            animation: alert-pulse 0.8s infinite;
        }

        @keyframes alert-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        .card-name {
            font-weight: 600;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--cyan);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            text-shadow: 0 0 8px var(--cyan), 0 0 16px rgba(0, 255, 249, 0.4);
        }

        .card.down .card-name {
            color: var(--red);
            text-shadow: 0 0 8px var(--red), 0 0 16px rgba(255, 0, 64, 0.4);
        }

        .card-metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.75rem;
            font-size: 0.8rem;
        }

        .metric {
            text-align: center;
            padding: 0.75rem 0.5rem;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            position: relative;
        }

        .metric-value {
            font-weight: 700;
            font-size: 1.25rem;
            margin-bottom: 0.35rem;
            color: var(--text);
            font-variant-numeric: tabular-nums;
            text-shadow: 0 0 8px rgba(224, 224, 224, 0.3);
        }

        .metric-label {
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-size: 0.65rem;
            text-shadow: 0 0 4px rgba(96, 96, 128, 0.3);
        }

        /* Segmented progress bar */
        .progress-bar {
            height: 3px;
            margin-top: 0.4rem;
            background: rgba(0, 0, 0, 0.4);
            position: relative;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            width: var(--progress-width, 0%);
            background: repeating-linear-gradient(
                90deg,
                var(--progress-color, var(--cyan)) 0px,
                var(--progress-color, var(--cyan)) 4px,
                transparent 4px,
                transparent 6px
            );
            box-shadow: 0 0 6px var(--progress-color, var(--cyan));
            transition: width 0.5s ease;
        }

        .progress-fill.warning {
            background: repeating-linear-gradient(
                90deg,
                var(--yellow) 0px,
                var(--yellow) 4px,
                transparent 4px,
                transparent 6px
            );
            box-shadow: 0 0 6px var(--yellow);
        }

        .progress-fill.danger {
            background: repeating-linear-gradient(
                90deg,
                var(--red) 0px,
                var(--red) 4px,
                transparent 4px,
                transparent 6px
            );
            box-shadow: 0 0 6px var(--red);
        }

        .progress-fill.orange {
            background: repeating-linear-gradient(
                90deg,
                var(--orange) 0px,
                var(--orange) 4px,
                transparent 4px,
                transparent 6px
            );
            box-shadow: 0 0 6px var(--orange);
        }

        .progress-fill.success {
            background: repeating-linear-gradient(
                90deg,
                var(--green) 0px,
                var(--green) 4px,
                transparent 4px,
                transparent 6px
            );
            box-shadow: 0 0 6px var(--green);
        }

        /* Pulse animation for data updates */
        @keyframes latencyPulse {
            0%, 100% { filter: brightness(1); }
            50% { filter: brightness(1.8); }
        }

        .progress-fill.pulse {
            animation: latencyPulse 0.2s ease-out;
        }

        .stats-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.5rem;
            margin-top: 0.75rem;
            font-size: 0.65rem;
            text-align: center;
        }

        .mini-stat {
            background: rgba(0, 0, 0, 0.2);
            padding: 0.4rem 0.25rem;
            border: 1px solid var(--border);
        }

        .mini-stat-value {
            font-weight: 600;
            color: var(--text);
            margin-bottom: 0.15rem;
            font-size: 0.75rem;
            font-variant-numeric: tabular-nums;
        }

        .mini-stat-label {
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.6rem;
        }

        .warning-banner {
            margin-top: 0.75rem;
            padding: 0.5rem 0.75rem;
            background: rgba(255, 136, 0, 0.1);
            border-left: 2px solid var(--orange);
            font-size: 0.7rem;
            color: var(--orange);
            display: flex;
            align-items: center;
            gap: 0.5rem;
            text-shadow: 0 0 6px var(--orange);
        }

        .warning-banner::before {
            content: '⚠';
            font-size: 0.9rem;
        }

        .card-footer {
            margin-top: 0.75rem;
            padding-top: 0.75rem;
            border-top: 1px solid var(--border);
            font-size: 0.7rem;
            color: var(--text-dim);
            display: flex;
            align-items: center;
            gap: 0.5rem;
            text-shadow: 0 0 4px rgba(96, 96, 128, 0.3);
        }

        .card-footer::before {
            content: '>';
            color: var(--cyan);
            text-shadow: 0 0 6px var(--cyan);
        }

        .error-text {
            color: var(--red);
            font-size: 0.7rem;
            margin-top: 0.75rem;
            padding: 0.5rem;
            background: rgba(255, 0, 64, 0.1);
            border-left: 2px solid var(--red);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            text-shadow: 0 0 6px var(--red);
            animation: errorFlicker 2s infinite;
        }

        .error-text::before {
            content: '[ERR] ';
            font-weight: 700;
        }

        .no-data {
            grid-column: 1 / -1;
            text-align: center;
            padding: 4rem 2rem;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.2em;
            font-size: 0.9rem;
            text-shadow: 0 0 6px rgba(96, 96, 128, 0.4);
        }

        .no-data::before {
            content: '// ';
            color: var(--cyan);
            text-shadow: 0 0 8px var(--cyan);
        }

        /* Glitch effect on hover */
        @keyframes glitch {
            0%, 100% { transform: translate(0); }
            20% { transform: translate(-2px, 2px); }
            40% { transform: translate(-2px, -2px); }
            60% { transform: translate(2px, 2px); }
            80% { transform: translate(2px, -2px); }
        }

        .card:hover .card-name {
            animation: glitch 0.3s ease;
        }

        /* Clickable card cursor */
        .card {
            cursor: pointer;
        }

        /* Modal styles */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(10, 10, 15, 0.92);
            backdrop-filter: blur(4px);
            z-index: 2000;
            justify-content: center;
            align-items: center;
            animation: modalFadeIn 0.2s ease-out;
        }

        .modal.active {
            display: flex;
        }

        @keyframes modalFadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .modal-content {
            background: var(--bg-panel);
            border: 1px solid var(--cyan);
            max-width: 800px;
            width: 90%;
            max-height: 85vh;
            display: flex;
            flex-direction: column;
            clip-path: polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 16px 100%, 0 calc(100% - 16px));
            box-shadow: 0 0 30px rgba(0, 255, 249, 0.3), 0 0 60px rgba(0, 255, 249, 0.1);
            animation: modalSlideIn 0.2s ease-out;
        }

        @keyframes modalSlideIn {
            from { transform: translateY(-20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border);
            background: rgba(0, 255, 249, 0.03);
        }

        .modal-title {
            font-size: 1rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            color: var(--cyan);
            text-shadow: 0 0 10px var(--cyan);
        }

        .modal-close {
            background: none;
            border: 1px solid var(--text-dim);
            color: var(--text-dim);
            width: 32px;
            height: 32px;
            font-size: 1.2rem;
            cursor: pointer;
            transition: all 0.2s ease;
            clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%);
        }

        .modal-close:hover {
            border-color: var(--red);
            color: var(--red);
            box-shadow: 0 0 10px var(--red);
        }

        .modal-summary {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--border);
        }

        .modal-stat {
            text-align: center;
        }

        .modal-stat-value {
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }

        .modal-stat-value.up { color: var(--green); text-shadow: 0 0 8px var(--green); }
        .modal-stat-value.down { color: var(--red); text-shadow: 0 0 8px var(--red); }

        .modal-stat-label {
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-dim);
        }

        .modal-body {
            flex: 1;
            overflow-y: auto;
            padding: 0;
        }

        .history-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.8rem;
        }

        .history-table thead {
            position: sticky;
            top: 0;
            background: var(--bg-panel);
            z-index: 10;
        }

        .history-table th {
            padding: 0.75rem 1rem;
            text-align: left;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-size: 0.7rem;
            color: var(--cyan);
            border-bottom: 1px solid var(--border);
            font-weight: 600;
        }

        .history-table td {
            padding: 0.6rem 1rem;
            border-bottom: 1px solid var(--border);
        }

        .history-table tr:hover td {
            background: rgba(0, 255, 249, 0.03);
        }

        .history-table .status-cell {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .history-table .status-dot {
            width: 8px;
            height: 8px;
            clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%);
        }

        .history-table .status-dot.up {
            background: var(--green);
            box-shadow: 0 0 6px var(--green);
        }

        .history-table .status-dot.down {
            background: var(--red);
            box-shadow: 0 0 6px var(--red);
        }

        .history-table .error-cell {
            color: var(--red);
            font-size: 0.75rem;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .history-loading {
            text-align: center;
            padding: 3rem;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

        .history-loading::before {
            content: '// ';
            color: var(--cyan);
        }

        .history-empty {
            text-align: center;
            padding: 3rem;
            color: var(--text-dim);
        }

        /* Graph visualization styles */
        .graphs-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border);
        }

        .graph-panel {
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            padding: 0.75rem;
            clip-path: polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 6px 100%, 0 calc(100% - 6px));
        }

        .graph-panel-wide {
            grid-column: 1 / -1;
        }

        .graph-title {
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--cyan);
            margin-bottom: 0.5rem;
            text-shadow: 0 0 6px var(--cyan);
        }

        .graph-container {
            width: 100%;
            height: 120px;
            position: relative;
        }

        .graph-panel-wide .graph-container {
            height: 100px;
        }

        .graph-container svg {
            width: 100%;
            height: 100%;
            overflow: visible;
        }

        .graph-empty {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: var(--text-dim);
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .graph-empty::before {
            content: '// ';
            color: var(--cyan);
        }

        /* SVG chart styles */
        .chart-line {
            fill: none;
            stroke: var(--cyan);
            stroke-width: 1.5;
            filter: drop-shadow(0 0 3px var(--cyan));
        }

        .chart-area {
            opacity: 0.3;
        }

        .chart-area-up {
            fill: var(--green);
        }

        .chart-area-down {
            fill: var(--red);
        }

        .chart-point {
            fill: var(--cyan);
            filter: drop-shadow(0 0 2px var(--cyan));
        }

        .chart-point:hover {
            filter: drop-shadow(0 0 6px var(--cyan));
        }

        .chart-bar {
            filter: drop-shadow(0 0 2px currentColor);
        }

        .chart-bar-2xx { fill: var(--green); }
        .chart-bar-3xx { fill: var(--cyan); }
        .chart-bar-4xx { fill: var(--yellow); }
        .chart-bar-5xx { fill: var(--red); }
        .chart-bar-other { fill: var(--text-dim); }

        .chart-bar-fast { fill: var(--green); }
        .chart-bar-medium { fill: var(--cyan); }
        .chart-bar-slow { fill: var(--yellow); }
        .chart-bar-veryslow { fill: var(--orange); }
        .chart-bar-timeout { fill: var(--red); }

        .chart-axis {
            stroke: var(--text-dim);
            stroke-width: 0.5;
        }

        .chart-grid {
            stroke: var(--border);
            stroke-width: 0.5;
            stroke-dasharray: 2, 4;
        }

        .chart-label {
            font-size: 8px;
            fill: var(--text-dim);
            font-family: 'JetBrains Mono', monospace;
        }

        .chart-value-label {
            font-size: 7px;
            fill: var(--text);
            font-family: 'JetBrains Mono', monospace;
        }

        /* Chart tooltip */
        .chart-tooltip {
            position: absolute;
            background: var(--bg-panel);
            border: 1px solid var(--cyan);
            padding: 0.4rem 0.6rem;
            font-size: 0.65rem;
            color: var(--text);
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.15s ease;
            z-index: 100;
            box-shadow: 0 0 8px rgba(0, 255, 249, 0.3);
            white-space: nowrap;
        }

        .chart-tooltip.visible {
            opacity: 1;
        }

        .chart-tooltip-time {
            color: var(--text-dim);
            font-size: 0.6rem;
        }

        .chart-tooltip-value {
            color: var(--cyan);
            font-weight: 600;
        }

        /* History table toggle */
        .history-toggle {
            padding: 0.75rem 1.5rem;
            border-bottom: 1px solid var(--border);
        }

        .history-toggle summary {
            cursor: pointer;
            color: var(--text-dim);
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            list-style: none;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .history-toggle summary::-webkit-details-marker {
            display: none;
        }

        .history-toggle summary::before {
            content: '▶';
            font-size: 0.6rem;
            transition: transform 0.2s ease;
        }

        .history-toggle[open] summary::before {
            transform: rotate(90deg);
        }

        .history-toggle summary:hover {
            color: var(--cyan);
        }

        /* Responsive graph adjustments */
        @media (max-width: 700px) {
            .graphs-grid {
                grid-template-columns: 1fr;
                padding: 0.75rem 1rem;
            }

            .graph-panel-wide {
                grid-column: 1;
            }

            .graph-container {
                height: 100px;
            }

            .graph-panel-wide .graph-container {
                height: 80px;
            }
        }

        /* Reset button in summary bar */
        .reset-button {
            background: none;
            border: 1px solid var(--text-dim);
            color: var(--text-dim);
            padding: 0.4rem 0.8rem;
            font-size: 0.75rem;
            font-family: 'JetBrains Mono', monospace;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-left: 1rem;
        }

        .reset-button:hover {
            border-color: var(--orange);
            color: var(--orange);
            box-shadow: 0 0 10px var(--orange);
        }

        /* Reset confirmation modal */
        .reset-modal-content {
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: 0;
            max-width: 500px;
            padding: 0;
            display: flex;
            flex-direction: column;
            max-height: 80vh;
        }

        .reset-modal-header {
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .reset-modal-title {
            font-size: 1rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--orange);
            text-shadow: 0 0 10px var(--orange);
        }

        .reset-modal-body {
            padding: 1.5rem;
            flex: 1;
            overflow-y: auto;
        }

        .reset-warning {
            background: rgba(255, 0, 64, 0.1);
            border-left: 3px solid var(--red);
            padding: 1rem;
            margin-bottom: 1rem;
            color: var(--red);
            font-size: 0.9rem;
            line-height: 1.5;
        }

        .reset-warning::before {
            content: '⚠ ';
            font-weight: 700;
        }

        .reset-modal-actions {
            padding: 1.25rem 1.5rem;
            border-top: 1px solid var(--border);
            display: flex;
            gap: 1rem;
            justify-content: flex-end;
        }

        .reset-button-cancel,
        .reset-button-confirm {
            padding: 0.5rem 1.25rem;
            font-size: 0.8rem;
            font-family: 'JetBrains Mono', monospace;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border: 1px solid;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .reset-button-cancel {
            background: none;
            border-color: var(--text-dim);
            color: var(--text-dim);
        }

        .reset-button-cancel:hover {
            border-color: var(--text);
            color: var(--text);
        }

        .reset-button-confirm {
            background: none;
            border-color: var(--red);
            color: var(--red);
            text-shadow: 0 0 8px var(--red);
        }

        .reset-button-confirm:hover {
            box-shadow: 0 0 10px var(--red);
        }

        .reset-button-confirm:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            box-shadow: none;
        }

        @media (max-width: 600px) {
            .modal-summary {
                grid-template-columns: repeat(2, 1fr);
            }
            .history-table th:nth-child(5),
            .history-table td:nth-child(5) {
                display: none;
            }
            .summary-bar {
                flex-wrap: wrap;
                gap: 0.5rem;
            }
            .reset-button {
                margin-left: 0;
                flex: 1;
            }
        }

        /* Accessibility: Skip link */
        .skip-link {
            position: absolute;
            top: -100px;
            left: 0;
            background: var(--bg-panel);
            color: var(--cyan);
            padding: 0.75rem 1.5rem;
            z-index: 3000;
            text-decoration: none;
            font-size: 0.9rem;
            border: 1px solid var(--cyan);
            transition: top 0.2s ease;
        }

        .skip-link:focus {
            top: 0;
            outline: 2px solid var(--cyan);
            outline-offset: 2px;
        }

        /* Accessibility: Enhanced focus styles */
        :focus {
            outline: 2px solid var(--cyan);
            outline-offset: 2px;
        }

        :focus:not(:focus-visible) {
            outline: none;
        }

        :focus-visible {
            outline: 2px solid var(--cyan);
            outline-offset: 2px;
        }

        .card:focus-visible {
            border-color: var(--cyan);
            box-shadow: 0 0 15px rgba(0, 255, 249, 0.25),
                0 0 30px rgba(0, 255, 249, 0.15),
                inset 0 0 20px rgba(0, 255, 249, 0.05);
            outline: 2px solid var(--cyan);
            outline-offset: 4px;
        }

        .card.down:focus-visible {
            border-color: var(--red);
            box-shadow: 0 0 15px rgba(255, 0, 64, 0.35),
                0 0 30px rgba(255, 0, 64, 0.2),
                inset 0 0 20px rgba(255, 0, 64, 0.05);
            outline-color: var(--red);
        }

        .modal-close:focus-visible {
            border-color: var(--cyan);
            color: var(--cyan);
            box-shadow: 0 0 10px var(--cyan);
        }

        .reset-button:focus-visible {
            border-color: var(--cyan);
            color: var(--cyan);
            box-shadow: 0 0 10px var(--cyan);
        }

        /* Accessibility: Improved color contrast */
        .metric-label {
            color: #9090a8;  /* Improved from #606080 for better contrast */
        }

        .updated-time {
            color: #9090a8;  /* Improved contrast */
        }

        .live-indicator {
            color: #9090a8;  /* Improved contrast */
        }

        .card-footer {
            color: #9090a8;  /* Improved contrast */
        }

        /* Accessibility: Visually hidden utility for screen readers */
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }
    </style>
</head>
<body>
    <a href="#cardsContainer" class="skip-link">Skip to main content</a>
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
            </section>
            <section class="modal-body" aria-label="Service analytics and history">
                <!-- Graph visualization panels -->
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
                <!-- Collapsible history table -->
                <details class="history-toggle">
                    <summary>Raw History Data</summary>
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
                </details>
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
    <script nonce="__CSP_NONCE__">
        const POLL_INTERVAL = 10000;
        const FETCH_TIMEOUT_MS = 10000;  // 10 second timeout for API requests
        let isUpdating = false;

        // Helper function to fetch with timeout
        async function fetchWithTimeout(url, options = {}) {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
            try {
                const response = await fetch(url, { ...options, signal: controller.signal });
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

        function renderCard(url) {
            const statusClass = url.is_up ? 'up' : 'down';
            const cardClass = url.is_up ? '' : ' down';
            const statusCode = url.status_code !== null ? url.status_code : '---';
            const errorHtml = url.error
                ? `<div class="error-text" title="${escapeHtml(url.error)}" role="alert">${escapeHtml(url.error)}</div>`
                : '';

            const latencyPercent = getLatencyPercent(url.response_time_ms);
            const latencyClass = getLatencyClass(url.response_time_ms);
            const uptimePercent = url.uptime_24h !== null ? url.uptime_24h : 0;
            const uptimeColor = getUptimeColor(url.uptime_24h);

            // Build stats row HTML (avg/min/max response times)
            const hasResponseStats = url.avg_response_time_24h !== null ||
                                     url.min_response_time_24h !== null ||
                                     url.max_response_time_24h !== null;
            const statsRowHtml = hasResponseStats ? `
                <div class="stats-row" aria-hidden="true">
                    <div class="mini-stat">
                        <div class="mini-stat-value">${formatResponseTime(url.avg_response_time_24h)}</div>
                        <div class="mini-stat-label">Avg</div>
                    </div>
                    <div class="mini-stat">
                        <div class="mini-stat-value">${formatResponseTime(url.min_response_time_24h)}</div>
                        <div class="mini-stat-label">Min</div>
                    </div>
                    <div class="mini-stat">
                        <div class="mini-stat-value">${formatResponseTime(url.max_response_time_24h)}</div>
                        <div class="mini-stat-label">Max</div>
                    </div>
                </div>
            ` : '';

            // Build warning banner for consecutive failures
            const warningHtml = url.consecutive_failures > 0 ? `
                <div class="warning-banner" role="alert">
                    ${url.consecutive_failures} consecutive failure${url.consecutive_failures > 1 ? 's' : ''}
                    ${url.last_downtime ? ' • Last down: ' + formatRelativeTime(url.last_downtime) : ''}
                </div>
            ` : '';

            // Build footer with last check and content length
            const contentInfo = url.content_length !== null ? ` • Size: ${formatBytes(url.content_length)}` : '';

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
                            <div class="metric-value">${statusCode}</div>
                            <div class="metric-label">Status</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${formatResponseTime(url.response_time_ms)}</div>
                            <div class="metric-label">Latency</div>
                            <div class="progress-bar" role="progressbar"
                                aria-valuenow="${url.response_time_ms || 0}"
                                aria-valuemin="0" aria-valuemax="2000"
                                aria-label="Latency indicator">
                                <div class="progress-fill ${latencyClass}" data-width="${latencyPercent}"></div>
                            </div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${formatUptime(url.uptime_24h)}</div>
                            <div class="metric-label">Uptime</div>
                            <div class="progress-bar" role="progressbar"
                                aria-valuenow="${uptimePercent}"
                                aria-valuemin="0" aria-valuemax="100"
                                aria-label="Uptime indicator">
                                <div class="progress-fill"
                                    data-width="${uptimePercent}"
                                    data-color="${uptimeColor}"></div>
                            </div>
                        </div>
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
            } catch (error) {
                console.error('Error fetching status:', error);
                document.getElementById('updatedTime').textContent = '// ERROR: CONNECTION_FAILED';
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

        function initializeDashboardData() {
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

            // Start polling for updates
            setInterval(fetchStatus, POLL_INTERVAL);
        }

        initializeDashboard();

        // Modal functionality
        let currentUrlData = null;
        let lastFocusedElement = null;  // Track element that opened modal

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

            modal.classList.add('active');

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

            // Return focus to the element that opened the modal
            if (lastFocusedElement) {
                lastFocusedElement.focus();
                lastFocusedElement = null;
            }
        }

        async function fetchHistory(urlName) {
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
                renderHistoryTable(data.checks);
                renderAllCharts(data.checks);
            } catch (error) {
                console.error('Error fetching history:', error);
                document.getElementById('historyTableBody').innerHTML =
                    '<tr><td colspan="5" class="history-empty">// ERROR: FAILED_TO_LOAD_HISTORY</td></tr>';
                // Show error state in charts
                ['responseTimeChart', 'uptimeChart', 'statusCodeChart', 'latencyHistogram'].forEach(id => {
                    showEmptyState(document.getElementById(id), 'Error loading data');
                });
            }
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

        function formatChartTime(isoString) {
            const date = new Date(isoString);
            return date.toLocaleTimeString(navigator.language, {
                hour: '2-digit',
                minute: '2-digit'
            });
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

            // Draw points (only if not too many)
            const tooltip = createTooltip(container);
            if (data.length <= 30) {
                data.forEach(c => {
                    const x = xScale(new Date(c.checked_at).getTime());
                    const y = yScale(c.response_time_ms);
                    const point = createSvgElement('circle', {
                        cx: x, cy: y, r: 3,
                        class: 'chart-point'
                    });

                    point.addEventListener('mouseenter', (e) => {
                        const content = `<div class="chart-tooltip-time">${formatChartTime(c.checked_at)}</div>
                            <div class="chart-tooltip-value">${c.response_time_ms}ms</div>`;
                        showTooltip(tooltip, e.offsetX, e.offsetY, content, rect);
                    });
                    point.addEventListener('mouseleave', () => hideTooltip(tooltip));

                    svg.appendChild(point);
                });
            }

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
                const label = createSvgElement('text', {
                    x: x + barWidth / 2,
                    y: height - padding.bottom + 12,
                    class: 'chart-label',
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
                const label = createSvgElement('text', {
                    x: x + barWidth / 2,
                    y: height - padding.bottom + 12,
                    class: 'chart-label',
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

        // Button event listeners (CSP-compliant, no inline handlers)
        document.getElementById('resetDataBtn').addEventListener('click', showResetModal);
        document.getElementById('historyModalClose').addEventListener('click', closeModal);
        document.getElementById('resetModalClose').addEventListener('click', cancelReset);
        document.getElementById('resetCancelBtn').addEventListener('click', cancelReset);
        document.getElementById('confirmResetBtn').addEventListener('click', confirmReset);

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
    </script>
</body>
</html>"""

# Split HTML at the initial data marker for efficient concatenation
# This avoids creating a new 35KB+ string on every request
_HTML_PARTS = HTML_DASHBOARD.split("__INITIAL_DATA__")
HTML_DASHBOARD_PREFIX = _HTML_PARTS[0].encode("utf-8")
HTML_DASHBOARD_SUFFIX = _HTML_PARTS[1].encode("utf-8")

# CSP nonce placeholder for runtime replacement
CSP_NONCE_PLACEHOLDER = "__CSP_NONCE__"
