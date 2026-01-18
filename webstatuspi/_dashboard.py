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
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');

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
            box-shadow: 0 0 15px rgba(0, 255, 249, 0.25), 0 0 30px rgba(0, 255, 249, 0.15), inset 0 0 20px rgba(0, 255, 249, 0.05);
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
            box-shadow: 0 0 15px rgba(255, 0, 64, 0.35), 0 0 30px rgba(255, 0, 64, 0.2), inset 0 0 20px rgba(255, 0, 64, 0.05);
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
            background: repeating-linear-gradient(
                90deg,
                var(--cyan) 0px,
                var(--cyan) 4px,
                transparent 4px,
                transparent 6px
            );
            box-shadow: 0 0 6px var(--cyan);
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
    </style>
</head>
<body>
    <div class="scanline-overlay"></div>
    <header>
        <h1>&lt;WebStatusPi/&gt;</h1>
        <div class="live-indicator">
            <span class="live-dot" id="liveDot"></span>
            <span>// LIVE FEED [10 sec]</span>
        </div>
    </header>
    <div class="summary-bar">
        <div class="summary-counts">
            <span class="count-up" id="countUp">[0] ONLINE</span>
            <span class="count-down" id="countDown">[0] OFFLINE</span>
        </div>
        <div>
            <span class="updated-time" id="updatedTime">// INITIALIZING...</span>
            <button class="reset-button" onclick="showResetModal()" title="Reset all monitoring data">// RESET DATA</button>
        </div>
    </div>
    <main id="cardsContainer">
        <div class="no-data">LOADING_SYSTEM_STATUS...</div>
    </main>

    <!-- History Modal -->
    <div class="modal" id="historyModal">
        <div class="modal-content">
            <div class="modal-header">
                <span class="modal-title" id="modalTitle">URL_NAME</span>
                <button class="modal-close" onclick="closeModal()" title="Close">&times;</button>
            </div>
            <div class="modal-summary" id="modalSummary">
                <div class="modal-stat">
                    <div class="modal-stat-value" id="modalStatus">---</div>
                    <div class="modal-stat-label">Status</div>
                </div>
                <div class="modal-stat">
                    <div class="modal-stat-value" id="modalCode">---</div>
                    <div class="modal-stat-label">Code</div>
                </div>
                <div class="modal-stat">
                    <div class="modal-stat-value" id="modalLatency">---</div>
                    <div class="modal-stat-label">Latency</div>
                </div>
                <div class="modal-stat">
                    <div class="modal-stat-value" id="modalUptime">---</div>
                    <div class="modal-stat-label">Uptime 24h</div>
                </div>
            </div>
            <div class="modal-body">
                <table class="history-table">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Status</th>
                            <th>Code</th>
                            <th>Latency</th>
                            <th>Error</th>
                        </tr>
                    </thead>
                    <tbody id="historyTableBody">
                        <tr><td colspan="5" class="history-loading">LOADING_HISTORY...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Reset Confirmation Modal -->
    <div class="modal" id="resetModal">
        <div class="reset-modal-content">
            <div class="reset-modal-header">
                <span class="reset-modal-title">Confirm Reset</span>
                <button class="modal-close" onclick="cancelReset()" title="Close">&times;</button>
            </div>
            <div class="reset-modal-body">
                <div class="reset-warning">This will delete all monitoring data. This action cannot be undone.</div>
                <p>Are you sure you want to reset all check records from the database?</p>
            </div>
            <div class="reset-modal-actions">
                <button class="reset-button-cancel" onclick="cancelReset()">Cancel</button>
                <button class="reset-button-confirm" id="confirmResetBtn" onclick="confirmReset()">Confirm Reset</button>
            </div>
        </div>
    </div>

    <script>
        const POLL_INTERVAL = 10000;
        let isUpdating = false;

        function formatTime(isoString) {
            const date = new Date(isoString);
            return date.toLocaleTimeString('en-US', { hour12: false });
        }

        function formatResponseTime(ms) {
            if (ms === null || ms === undefined || ms === 0) return '---';
            return ms + 'ms';
        }

        function formatUptime(uptime) {
            if (uptime === null || uptime === undefined) return '---';
            return uptime.toFixed(1) + '%';
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
            const errorHtml = url.error ? `<div class="error-text" title="${escapeHtml(url.error)}">${escapeHtml(url.error)}</div>` : '';

            const latencyPercent = getLatencyPercent(url.response_time_ms);
            const latencyClass = getLatencyClass(url.response_time_ms);
            const uptimePercent = url.uptime_24h !== null ? url.uptime_24h : 0;
            const uptimeColor = getUptimeColor(url.uptime_24h);

            return `
                <div class="card${cardClass}" onclick="openModal('${escapeHtml(url.name)}')">
                    <div class="card-anchor"></div>
                    <div class="card-header">
                        <span class="status-indicator ${statusClass}"></span>
                        <span class="card-name" title="${escapeHtml(url.name)}">${escapeHtml(url.name)}</span>
                    </div>
                    <div class="card-metrics">
                        <div class="metric">
                            <div class="metric-value">${statusCode}</div>
                            <div class="metric-label">Status</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${formatResponseTime(url.response_time_ms)}</div>
                            <div class="metric-label">Latency</div>
                            <div class="progress-bar">
                                <div class="progress-fill ${latencyClass}" style="width: ${latencyPercent}%"></div>
                            </div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${formatUptime(url.uptime_24h)}</div>
                            <div class="metric-label">Uptime</div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${uptimePercent}%; background: repeating-linear-gradient(90deg, ${uptimeColor} 0px, ${uptimeColor} 4px, transparent 4px, transparent 6px); box-shadow: 0 0 6px ${uptimeColor};"></div>
                            </div>
                        </div>
                    </div>
                    ${errorHtml}
                    <div class="card-footer">
                        LAST_SCAN: ${formatTime(url.last_check)}
                    </div>
                </div>
            `;
        }

        async function fetchStatus() {
            const liveDot = document.getElementById('liveDot');
            liveDot.classList.add('updating');
            isUpdating = true;

            try {
                const response = await fetch('/status');
                if (!response.ok) throw new Error('Failed to fetch status');

                const data = await response.json();

                const countUp = document.getElementById('countUp');
                const countDown = document.getElementById('countDown');
                countUp.textContent = '[' + data.summary.up + '] ONLINE';
                countDown.textContent = '[' + data.summary.down + '] OFFLINE';
                countUp.classList.toggle('count-dimmed', data.summary.up === 0);
                countDown.classList.toggle('count-dimmed', data.summary.down === 0);
                document.getElementById('updatedTime').textContent = '// SYNC: ' + new Date().toLocaleTimeString('en-US', { hour12: false });

                const container = document.getElementById('cardsContainer');
                if (data.urls.length === 0) {
                    container.innerHTML = '<div class="no-data">NO_TARGETS_CONFIGURED</div>';
                } else {
                    container.innerHTML = data.urls.map(renderCard).join('');
                    // Trigger pulse effect on latency bars
                    document.querySelectorAll('.progress-fill').forEach(bar => {
                        bar.classList.add('pulse');
                        setTimeout(() => bar.classList.remove('pulse'), 200);
                    });
                }
            } catch (error) {
                console.error('Error fetching status:', error);
                document.getElementById('updatedTime').textContent = '// ERROR: CONNECTION_FAILED';
            } finally {
                liveDot.classList.remove('updating');
                isUpdating = false;
            }
        }

        fetchStatus();
        setInterval(fetchStatus, POLL_INTERVAL);

        // Modal functionality
        let currentUrlData = null;

        function openModal(urlName) {
            const modal = document.getElementById('historyModal');
            const modalTitle = document.getElementById('modalTitle');
            const tableBody = document.getElementById('historyTableBody');

            modalTitle.textContent = urlName;
            tableBody.innerHTML = '<tr><td colspan="5" class="history-loading">LOADING_HISTORY...</td></tr>';

            // Reset summary values
            document.getElementById('modalStatus').textContent = '---';
            document.getElementById('modalStatus').className = 'modal-stat-value';
            document.getElementById('modalCode').textContent = '---';
            document.getElementById('modalLatency').textContent = '---';
            document.getElementById('modalUptime').textContent = '---';

            modal.classList.add('active');
            fetchHistory(urlName);
        }

        function closeModal() {
            const modal = document.getElementById('historyModal');
            modal.classList.remove('active');
        }

        async function fetchHistory(urlName) {
            try {
                // Fetch current status for summary
                const statusResponse = await fetch('/status/' + encodeURIComponent(urlName));
                if (statusResponse.ok) {
                    const statusData = await statusResponse.json();
                    updateModalSummary(statusData);
                }

                // Fetch history
                const historyResponse = await fetch('/history/' + encodeURIComponent(urlName));
                if (!historyResponse.ok) {
                    throw new Error('Failed to fetch history');
                }

                const data = await historyResponse.json();
                renderHistoryTable(data.checks);
            } catch (error) {
                console.error('Error fetching history:', error);
                document.getElementById('historyTableBody').innerHTML =
                    '<tr><td colspan="5" class="history-empty">// ERROR: FAILED_TO_LOAD_HISTORY</td></tr>';
            }
        }

        function updateModalSummary(data) {
            const statusEl = document.getElementById('modalStatus');
            statusEl.textContent = data.is_up ? 'ONLINE' : 'OFFLINE';
            statusEl.className = 'modal-stat-value ' + (data.is_up ? 'up' : 'down');

            document.getElementById('modalCode').textContent = data.status_code !== null ? data.status_code : '---';
            document.getElementById('modalLatency').textContent = formatResponseTime(data.response_time_ms);
            document.getElementById('modalUptime').textContent = formatUptime(data.uptime_24h);
        }

        function renderHistoryTable(checks) {
            const tableBody = document.getElementById('historyTableBody');

            if (!checks || checks.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="5" class="history-empty">// NO_HISTORY_DATA</td></tr>';
                return;
            }

            tableBody.innerHTML = checks.map(check => {
                const statusClass = check.is_up ? 'up' : 'down';
                const statusText = check.is_up ? 'UP' : 'DOWN';
                const code = check.status_code !== null ? check.status_code : '---';
                const latency = check.response_time_ms ? check.response_time_ms + 'ms' : '---';
                const error = check.error ? `<span class="error-cell" title="${escapeHtml(check.error)}">${escapeHtml(check.error)}</span>` : '---';
                const time = formatDateTime(check.checked_at);

                return `
                    <tr>
                        <td>${time}</td>
                        <td class="status-cell"><span class="status-dot ${statusClass}"></span>${statusText}</td>
                        <td>${code}</td>
                        <td>${latency}</td>
                        <td>${error}</td>
                    </tr>
                `;
            }).join('');
        }

        function formatDateTime(isoString) {
            const date = new Date(isoString);
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hours = String(date.getHours()).padStart(2, '0');
            const mins = String(date.getMinutes()).padStart(2, '0');
            const secs = String(date.getSeconds()).padStart(2, '0');
            return `${month}-${day} ${hours}:${mins}:${secs}`;
        }

        function showResetModal() {
            const resetModal = document.getElementById('resetModal');
            resetModal.classList.add('active');
            document.getElementById('confirmResetBtn').disabled = false;
        }

        function cancelReset() {
            const resetModal = document.getElementById('resetModal');
            resetModal.classList.remove('active');
        }

        function confirmReset() {
            const confirmBtn = document.getElementById('confirmResetBtn');
            confirmBtn.disabled = true;
            confirmBtn.textContent = 'RESETTING...';

            fetch('/reset', { method: 'DELETE' })
                .then(response => {
                    if (response.ok) {
                        return response.json();
                    }
                    throw new Error('Failed to reset data');
                })
                .then(data => {
                    cancelReset();
                    confirmBtn.textContent = 'Confirm Reset';
                    // Refresh the dashboard data
                    updateDashboard();
                })
                .catch(error => {
                    confirmBtn.disabled = false;
                    confirmBtn.textContent = 'Confirm Reset';
                    alert('Error: Failed to reset data. ' + error.message);
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
    </script>
</body>
</html>"""
