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
            box-shadow: 0 0 15px rgba(0, 255, 249, 0.25), 0 0 30px rgba(0, 255, 249, 0.15), inset 0 0 20px rgba(0, 255, 249, 0.05);
            outline: 2px solid var(--cyan);
            outline-offset: 4px;
        }

        .card.down:focus-visible {
            border-color: var(--red);
            box-shadow: 0 0 15px rgba(255, 0, 64, 0.35), 0 0 30px rgba(255, 0, 64, 0.2), inset 0 0 20px rgba(255, 0, 64, 0.05);
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
            <button class="reset-button" onclick="showResetModal()" aria-label="Reset all monitoring data" type="button">// RESET DATA</button>
        </div>
    </nav>
    <main id="cardsContainer" role="main" aria-label="Service status cards">
        <div class="no-data" role="status">LOADING_SYSTEM_STATUS...</div>
    </main>

    <!-- History Modal -->
    <div class="modal" id="historyModal" role="dialog" aria-modal="true" aria-labelledby="modalTitle" aria-describedby="modalDescription">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title" id="modalTitle">URL_NAME</h2>
                <button class="modal-close" onclick="closeModal()" aria-label="Close history modal" type="button">&times;</button>
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
            <section class="modal-body" aria-label="Check history">
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
            </section>
        </div>
    </div>

    <!-- Reset Confirmation Modal -->
    <div class="modal" id="resetModal" role="alertdialog" aria-modal="true" aria-labelledby="resetModalTitle" aria-describedby="resetWarningText">
        <div class="reset-modal-content">
            <div class="reset-modal-header">
                <h2 class="reset-modal-title" id="resetModalTitle">Confirm Reset</h2>
                <button class="modal-close" onclick="cancelReset()" aria-label="Cancel and close" type="button">&times;</button>
            </div>
            <div class="reset-modal-body">
                <div class="reset-warning" id="resetWarningText" role="alert">This will delete all monitoring data. This action cannot be undone.</div>
                <p>Are you sure you want to reset all check records from the database?</p>
            </div>
            <div class="reset-modal-actions">
                <button class="reset-button-cancel" onclick="cancelReset()" type="button">Cancel</button>
                <button class="reset-button-confirm" id="confirmResetBtn" onclick="confirmReset()" type="button">Confirm Reset</button>
            </div>
        </div>
    </div>

    <script id="initialData" type="application/json">__INITIAL_DATA__</script>
    <script>
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
            const date = new Date(isoString);
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
            const errorHtml = url.error ? `<div class="error-text" title="${escapeHtml(url.error)}" role="alert">${escapeHtml(url.error)}</div>` : '';

            const latencyPercent = getLatencyPercent(url.response_time_ms);
            const latencyClass = getLatencyClass(url.response_time_ms);
            const uptimePercent = url.uptime_24h !== null ? url.uptime_24h : 0;
            const uptimeColor = getUptimeColor(url.uptime_24h);

            const statusText = url.is_up ? 'online' : 'offline';
            const latencyText = url.response_time_ms ? url.response_time_ms + ' milliseconds' : 'unknown';
            const uptimeText = url.uptime_24h !== null ? url.uptime_24h.toFixed(1) + ' percent' : 'unknown';
            const ariaLabel = `${escapeHtml(url.name)}, ${statusText}, latency ${latencyText}, uptime ${uptimeText}. Press Enter or Space to view history.`;

            return `
                <article class="card${cardClass}"
                    tabindex="0"
                    role="button"
                    aria-label="${ariaLabel}"
                    data-url-name="${escapeHtml(url.name)}"
                    onclick="openModal('${escapeHtml(url.name)}')"
                    onkeydown="handleCardKeydown(event, '${escapeHtml(url.name)}')">
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
                            <div class="progress-bar" role="progressbar" aria-valuenow="${url.response_time_ms || 0}" aria-valuemin="0" aria-valuemax="2000" aria-label="Latency indicator">
                                <div class="progress-fill ${latencyClass}" style="width: ${latencyPercent}%"></div>
                            </div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${formatUptime(url.uptime_24h)}</div>
                            <div class="metric-label">Uptime</div>
                            <div class="progress-bar" role="progressbar" aria-valuenow="${uptimePercent}" aria-valuemin="0" aria-valuemax="100" aria-label="Uptime indicator">
                                <div class="progress-fill" style="width: ${uptimePercent}%; background: repeating-linear-gradient(90deg, ${uptimeColor} 0px, ${uptimeColor} 4px, transparent 4px, transparent 6px); box-shadow: 0 0 6px ${uptimeColor};"></div>
                            </div>
                        </div>
                    </div>
                    ${errorHtml}
                    <footer class="card-footer">
                        LAST_SCAN: ${formatTime(url.last_check)}
                    </footer>
                </article>
            `;
        }

        function handleCardKeydown(event, urlName) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                openModal(urlName);
            }
        }

        function renderDashboard(data, showPulse = true) {
            const countUp = document.getElementById('countUp');
            const countDown = document.getElementById('countDown');
            countUp.textContent = '[' + data.summary.up + '] ONLINE';
            countDown.textContent = '[' + data.summary.down + '] OFFLINE';
            // Update aria-labels with current counts
            countUp.setAttribute('aria-label', data.summary.up + ' services online');
            countDown.setAttribute('aria-label', data.summary.down + ' services offline');
            countUp.classList.toggle('count-dimmed', data.summary.up === 0);
            countDown.classList.toggle('count-dimmed', data.summary.down === 0);
            document.getElementById('updatedTime').textContent = '// SYNC: ' + new Date().toLocaleTimeString('en-US', { hour12: false });

            const container = document.getElementById('cardsContainer');
            if (data.urls.length === 0) {
                container.innerHTML = '<div class="no-data" role="status">NO_TARGETS_CONFIGURED</div>';
            } else {
                container.innerHTML = data.urls.map(renderCard).join('');
                // Trigger pulse effect on latency bars
                if (showPulse) {
                    document.querySelectorAll('.progress-fill').forEach(bar => {
                        bar.classList.add('pulse');
                        setTimeout(() => bar.classList.remove('pulse'), 200);
                    });
                }
            }
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
            tableBody.innerHTML = '<tr><td colspan="5" class="history-loading" role="status">LOADING_HISTORY...</td></tr>';

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
            } catch (error) {
                console.error('Error fetching history:', error);
                document.getElementById('historyTableBody').innerHTML =
                    '<tr><td colspan="5" class="history-empty">// ERROR: FAILED_TO_LOAD_HISTORY</td></tr>';
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
                tableBody.innerHTML = '<tr><td colspan="5" class="history-empty" role="status">// NO_HISTORY_DATA</td></tr>';
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
                        <td class="status-cell"><span class="status-dot ${statusClass}" aria-hidden="true"></span><span class="sr-only">Status: </span>${statusText}</td>
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
    </script>
</body>
</html>"""

# Split HTML at the initial data marker for efficient concatenation
# This avoids creating a new 35KB+ string on every request
_HTML_PARTS = HTML_DASHBOARD.split("__INITIAL_DATA__")
HTML_DASHBOARD_PREFIX = _HTML_PARTS[0].encode("utf-8")
HTML_DASHBOARD_SUFFIX = _HTML_PARTS[1].encode("utf-8")
