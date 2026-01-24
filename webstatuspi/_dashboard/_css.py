"""CSS styles for the dashboard.

This module contains all CSS styles embedded in the dashboard HTML.
Separated from the main dashboard module for maintainability.
"""

CSS_STYLES = """
        :root {
            --bg-dark: #0a0a0f;
            --bg-panel: #12121a;
            --cyan: #00fff9;  /* Bright cyan - WCAG AA compliant against dark backgrounds */
            --magenta: #ff00ff;
            --yellow: #f0ff00;
            --orange: #ff8800;
            --green: #00ff66;
            --red: #ff0040;
            --text: #e0e0e0;
            --text-dim: #9090a8;  /* Improved from #606080 for WCAG AA contrast */
            --border: #2a2a3a;
            /* ========================================
               LAYOUT GRID SYSTEM - Strict Alignment
               ======================================== */
            --gutter: 20px;           /* Universal left/right margin */
            --box-padding: 20px;      /* Internal padding for all boxes */
            --gap: 12px;              /* Gap between grid cells */
            --card-max-width: 420px;  /* Max width for cards */
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            /* Use system monospace fonts for zero-dependency deployment */
            font-family: 'Fira Code', 'Consolas', 'Monaco', 'Menlo', monospace;
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
            padding: 16px var(--gutter);
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

        .logo-text {
            font-weight: 600;
            letter-spacing: 0.1em;
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
            padding: 12px var(--gutter);
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
            padding: var(--gutter);
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, var(--card-max-width)));
            gap: var(--gutter);
            max-width: calc(var(--card-max-width) * 2 + var(--gutter) * 3);
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
            padding: var(--box-padding);
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
            justify-content: flex-start;
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
            text-align: left;
            margin-left: 0;
        }

        .card.down .card-name {
            color: var(--red);
            text-shadow: 0 0 8px var(--red), 0 0 16px rgba(255, 0, 64, 0.4);
        }

        /* ========================================
           DATA GRID - 4 Column System
           ======================================== */
        .card-metrics {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: var(--gap);
        }

        .metric {
            text-align: left;
            padding: 10px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .metric-label {
            color: #9090a8;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.55rem;
            line-height: 1;
        }

        .metric-value {
            font-weight: 700;
            font-size: 1.1rem;
            color: var(--text);
            font-variant-numeric: tabular-nums;
            text-shadow: 0 0 8px rgba(224, 224, 224, 0.3);
            line-height: 1.2;
        }

        /* Latency warning prefix styling */
        .latency-warning-prefix {
            font-size: 0.7rem;
            font-weight: 700;
            margin-right: 0.25rem;
        }

        .latency-warning-prefix.warning {
            color: var(--yellow);
            text-shadow: 0 0 6px var(--yellow);
        }

        .latency-warning-prefix.danger {
            color: var(--red);
            text-shadow: 0 0 6px var(--red);
        }

        .metric-empty {
            background: transparent;
            border: none;
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
            grid-template-columns: repeat(4, 1fr);
            gap: var(--gap);
            margin-top: var(--gap);
        }

        .mini-stat {
            background: rgba(0, 0, 0, 0.2);
            padding: 8px 10px;
            border: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            gap: 4px;
            text-align: left;
        }

        .mini-stat-label {
            color: #9090a8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.5rem;
            line-height: 1;
        }

        .mini-stat-value {
            font-weight: 600;
            color: var(--text);
            font-size: 0.75rem;
            font-variant-numeric: tabular-nums;
            line-height: 1.2;
        }

        .warning-banner {
            margin-top: 0.5rem;
            padding: 0.4rem 0.6rem;
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
            content: '\u26a0';
            font-size: 0.9rem;
        }

        .card-footer {
            margin-top: 0.5rem;
            padding-top: 0.5rem;
            border-top: 1px solid var(--border);
            font-size: 0.65rem;
            color: #9090a8;
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
            margin-top: 0.5rem;
            padding: 0.4rem;
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
            padding: 16px var(--box-padding);
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
            width: 44px;
            height: 44px;
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
            grid-template-columns: repeat(5, 1fr);
            gap: var(--gap);
            padding: var(--box-padding);
            border-bottom: 1px solid var(--border);
        }

        .modal-stat {
            text-align: center;
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .modal-stat-value {
            font-size: 1.4rem;
            font-weight: 700;
            line-height: 1.2;
        }

        .modal-stat-value.up { color: var(--green); text-shadow: 0 0 8px var(--green); }
        .modal-stat-value.down { color: var(--red); text-shadow: 0 0 8px var(--red); }

        .modal-stat-label {
            font-size: 0.6rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #9090a8;
            line-height: 1;
        }

        /* Modal URL bar */
        .modal-url-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px var(--box-padding);
            border-bottom: 1px solid var(--border);
            font-size: 0.75rem;
            background: rgba(0, 0, 0, 0.2);
        }

        .modal-url-info,
        .modal-server-info {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .modal-url-label,
        .modal-server-label,
        .modal-status-label {
            color: #8899A6;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .modal-url-value {
            color: var(--cyan);
            text-shadow: 0 0 6px var(--cyan);
        }

        .modal-server-value {
            color: var(--cyan);
            text-shadow: 0 0 6px var(--cyan);
            margin-right: 1rem;
        }

        .modal-status-value {
            color: var(--green);
            text-shadow: 0 0 6px var(--green);
        }

        /* Modal Additional Details - Direct Display */
        .modal-additional-details {
            border-bottom: 1px solid var(--border);
            padding: 12px var(--box-padding);
        }

        .modal-metrics-container {
            display: flex;
            align-items: flex-start;
            gap: 2rem;
            font-size: 0.75rem;
        }

        .modal-metrics-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            flex: 1;
        }

        .modal-metrics-row {
            display: flex;
            align-items: center;
            gap: 1.5rem;
            font-size: 0.75rem;
        }

        .modal-metrics-title {
            color: #8899A6;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.65rem;
            font-weight: 600;
            min-width: 80px;
        }

        .modal-metric-item {
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }

        .modal-metric-label {
            color: #8899A6;
            font-size: 0.65rem;
        }

        .modal-metric-value {
            color: var(--cyan);
            font-weight: 600;
            text-shadow: 0 0 6px var(--cyan);
        }

        /* Percentile visual hierarchy */
        .modal-metric-item[data-metric="p50"] .modal-metric-value {
            opacity: 0.7;
            font-weight: 500;
        }

        .modal-metric-item[data-metric="p95"] .modal-metric-value {
            font-weight: 600;
        }

        .modal-metric-item[data-metric="p99"] .modal-metric-value {
            color: var(--orange);
            text-shadow: 0 0 8px var(--orange);
            font-weight: 700;
            font-size: 0.8rem;
        }

        .modal-value-green {
            color: var(--green);
            text-shadow: 0 0 6px var(--green);
        }

        .modal-value-orange {
            color: var(--orange);
            text-shadow: 0 0 6px var(--orange);
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
            padding: 12px var(--box-padding);
            text-align: left;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-size: 0.7rem;
            color: var(--cyan);
            border-bottom: 1px solid var(--border);
            font-weight: 600;
        }

        .history-table td {
            padding: 10px var(--box-padding);
            border-bottom: 1px solid var(--border);
            line-height: 1.5;
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
            gap: var(--gap);
            padding: var(--box-padding);
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

        .chart-hover-line {
            stroke: var(--text-dim);
            stroke-width: 1;
            stroke-dasharray: 3, 3;
            pointer-events: none;
        }

        .chart-hover-point {
            fill: var(--cyan);
            stroke: var(--bg-panel);
            stroke-width: 2;
            filter: drop-shadow(0 0 4px var(--cyan));
            pointer-events: none;
        }

        .chart-overlay {
            cursor: crosshair;
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

        /* Label colors - darker versions for readability */
        .chart-label-2xx { fill: #00994d; }
        .chart-label-3xx { fill: #009994; }
        .chart-label-4xx { fill: #909900; }
        .chart-label-5xx { fill: #cc0033; }
        .chart-label-other { fill: var(--text-dim); }
        .chart-label-fast { fill: #00994d; }
        .chart-label-medium { fill: #009994; }
        .chart-label-slow { fill: #909900; }
        .chart-label-veryslow { fill: #cc6600; }
        .chart-label-timeout { fill: #cc0033; }

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
            fill: var(--bg-panel);
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
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

        /* Modal Tabs */
        .modal-tabs {
            display: flex;
            padding: 0 var(--box-padding);
            padding-top: 1rem;
            background: var(--bg-panel);
            position: relative;
        }

        .modal-tabs::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 1px;
            background: var(--border);
        }

        .modal-tab {
            padding: 0.6rem 1.25rem;
            cursor: pointer;
            color: var(--text-dim);
            font-size: 0.75rem;
            font-family: 'JetBrains Mono', monospace;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            text-align: center;
            background: none;
            border: 1px solid transparent;
            border-bottom: none;
            margin-bottom: -1px;
            position: relative;
            transition: all 0.2s ease;
            min-height: 44px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }

        .modal-tab:hover:not(.active) {
            color: var(--cyan);
        }

        .modal-tab.active {
            color: var(--cyan);
            background: var(--bg-panel);
            border-color: var(--border);
            border-bottom: 1px solid var(--bg-panel);
            z-index: 1;
        }

        .modal-tab-content {
            display: none;
        }

        .modal-tab-content.active {
            display: block;
        }

        #historyTab {
            padding: var(--box-padding);
        }

        /* Responsive graph adjustments */
        /* Responsive adjustments */
        @media (max-width: 768px) {
             main {
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            }
        }

        @media (max-width: 600px) {
            :root {
                --gutter: 12px;
                --box-padding: 12px;
                --gap: 8px;
            }
            
            main {
                padding: var(--gutter);
                /* Ensure single column on narrow screens but allow full width */
                grid-template-columns: 1fr;
                max-width: 100%;
            }

            header {
                flex-direction: column;
                gap: 0.75rem;
                padding-bottom: 12px;
            }

            .summary-bar {
                flex-direction: column;
                gap: 0.75rem;
                height: auto;
                align-items: stretch;
            }

            .summary-counts {
                justify-content: center;
                width: 100%;
                gap: 2rem;
            }

            .summary-actions {
                width: 100%;
                justify-content: space-between;
                flex-wrap: nowrap;
            }

            .install-button,
            .reset-button {
                flex: 1;
                padding: 0.6rem; /* Larger touch target */
            }

            .updated-time {
                display: none; /* Hide time in summary bar on mobile to save space, it's in header/cards */
            }

            .card-metrics {
                grid-template-columns: repeat(2, 1fr);
            }

            .card-metrics .metric-empty {
                display: none;
            }

            /* Optimize Modal for Mobile */
            .modal-content {
                width: 95%;
                max-height: 92vh;
                margin: 0;
                clip-path: none; /* Remove aesthetic clip-path for max space */
                border-radius: 4px; /* Simple radius instead */
            }

            .modal-header {
                padding: 12px;
            }
            
            .modal-close {
                width: 48px; /* Larger touch target */
                height: 48px;
            }

            .modal-summary {
                grid-template-columns: repeat(2, 1fr); /* 2 cols */
                gap: 12px;
            }
            
            /* Make status full width in summary */
            .modal-stat:first-child {
                grid-column: 1 / -1;
                padding-bottom: 8px;
                border-bottom: 1px solid var(--border);
                margin-bottom: 4px;
            }

            .modal-url-bar {
                flex-direction: column;
                gap: 0.75rem;
                align-items: flex-start;
            }
            
            .modal-url-info, .modal-server-info {
                flex-wrap: wrap;
            }
            
            .modal-server-info {
                width: 100%;
                justify-content: space-between;
            }
            
            .modal-server-value {
                margin-right: 0;
            }

            .stats-row {
                grid-template-columns: repeat(2, 1fr);
            }

            .history-table th:nth-child(4), /* Latency */
            .history-table td:nth-child(4),
            .history-table th:nth-child(5), /* Error */
            .history-table td:nth-child(5) {
                display: none; /* Hide more columns on mobile */
            }
            
            /* Show status code and time only */
            
            .modal-metrics-row {
                flex-wrap: wrap;
                gap: 1rem;
            }
            
            .modal-metrics-title {
                width: 100%;
                margin-bottom: 0.5rem;
                color: var(--cyan); /* Highlight titles on mobile */
            }

            /* Better touch targets for tabs */
            .modal-tab {
                flex: 1;
                padding: 1rem 0.5rem;
            }
        }
        
        /* Small mobile devices */
        @media (max-width: 360px) {
            header h1 { font-size: 1rem; }
            .logo-bracket { display: none; } /* Simplify logo */
            
            .card-metrics {
                gap: 4px;
            }
            
            .metric {
                padding: 8px;
            }
            
            .metric-value {
                font-size: 1rem;
            }
        }

        /* Touch interaction improvements */
        @media (hover: none) {
            .card:hover {
                /* Remove hover transform on touch */
                transform: none;
                box-shadow: 0 0 8px rgba(0, 255, 249, 0.1);
                border-color: var(--border);
            }
            
            .card:hover .card-name {
                animation: none;
            }
            
            /* Active state for touch feedback */
            .card:active {
                border-color: var(--cyan);
                background: rgba(0, 255, 249, 0.05);
            }
            
            /* Ensure scrollable areas are obvious */
            .modal-body {
                -webkit-overflow-scrolling: touch;
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

        /* Offline banner - uses hidden attribute (CSP-safe, no inline styles) */
        .offline-banner {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: var(--red);
            color: white;
            text-align: center;
            padding: 0.5rem;
            z-index: 10000;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            animation: errorFlicker 2s infinite;
        }

        /* Accessibility: Respect user preference for reduced motion (WCAG 2.3.3) */
        @media (prefers-reduced-motion: reduce) {
            *,
            *::before,
            *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }

            .scanline-overlay {
                display: none;
            }

            body {
                animation: none;
            }

            .live-dot {
                animation: none;
            }

            .card.down {
                animation: none;
            }

            .status-indicator.down::before {
                animation: none;
            }

            .offline-banner {
                animation: none;
            }

            .error-text {
                animation: none;
            }

            .progress-fill.pulse {
                animation: none;
            }
        }
"""
