"""Service Worker registration JavaScript for dashboard HTML.

This JavaScript snippet should be added to the dashboard HTML to register
the service worker and handle updates.
"""

# SERVICE WORKER REGISTRATION CODE (for dashboard HTML)
# This JavaScript snippet should be added to the dashboard HTML to register
# the service worker and handle updates.

SW_REGISTRATION_JS = """
        // ========================================
        // PWA: Service Worker Registration
        // ========================================
        if ('serviceWorker' in navigator) {
            // Auto-refresh when a new SW takes control
            let refreshing = false;
            navigator.serviceWorker.addEventListener('controllerchange', () => {
                if (refreshing) return;
                refreshing = true;
                console.log('[PWA] New version activated, refreshing...');
                window.location.reload();
            });

            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/sw.js')
                    .then(registration => {
                        console.log('[PWA] Service Worker registered');

                        // Check for updates every 60 seconds
                        setInterval(() => {
                            registration.update();
                        }, 60000);

                        // Handle updates - trigger skipWaiting on new SW
                        registration.addEventListener('updatefound', () => {
                            const newWorker = registration.installing;
                            newWorker.addEventListener('statechange', () => {
                                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                    console.log('[PWA] New version installed, activating...');
                                    newWorker.postMessage({ type: 'SKIP_WAITING' });
                                }
                            });
                        });
                    })
                    .catch(error => {
                        console.error('[PWA] Service Worker registration failed:', error);
                    });
            });
        }

        // ========================================
        // PWA: Online/Offline Detection (uses CSS class, no inline styles due to CSP)
        // ========================================
        function updateOnlineStatus() {
            if (navigator.onLine) {
                document.body.classList.remove('offline');
                // Refresh data when coming back online
                fetchStatus();
            } else {
                document.body.classList.add('offline');
            }
        }

        window.addEventListener('online', updateOnlineStatus);
        window.addEventListener('offline', updateOnlineStatus);

        // Check initial status
        if (!navigator.onLine) {
            updateOnlineStatus();
        }
"""
