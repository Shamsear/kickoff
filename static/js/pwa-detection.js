// PWA Detection and Mobile Installation Enforcement
class PWAController {
    constructor() {
        this.isMobile = this.detectMobile();
        this.isPWA = this.detectPWA();
        this.isStandalone = this.detectStandalone();
        this.deferredPrompt = null;
        
        this.init();
    }

    // Detect if device is mobile
    detectMobile() {
        return /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
               (navigator.maxTouchPoints && navigator.maxTouchPoints > 2) ||
               window.innerWidth <= 768;
    }

    // Detect if opened as PWA (standalone mode)
    detectPWA() {
        return window.matchMedia('(display-mode: standalone)').matches ||
               window.navigator.standalone === true ||
               document.referrer.includes('android-app://');
    }

    // Detect standalone mode (iOS)
    detectStandalone() {
        return window.navigator.standalone || 
               window.matchMedia('(display-mode: standalone)').matches;
    }

    // Initialize PWA controller
    init() {
        console.log('PWA Controller initialized:', {
            isMobile: this.isMobile,
            isPWA: this.isPWA,
            isStandalone: this.isStandalone
        });

        // Handle mobile browser access
        if (this.isMobile && !this.isPWA && !this.isStandalone) {
            this.showInstallScreen();
        }

        // Register service worker
        this.registerServiceWorker();

        // Listen for install prompt
        this.setupInstallPrompt();

        // Setup mobile optimizations for PWA mode
        if (this.isMobile && (this.isPWA || this.isStandalone)) {
            this.enableMobileOptimizations();
        }
    }

    // Show installation required screen for mobile browsers
    showInstallScreen() {
        // Hide main content
        const mainContent = document.querySelector('main') || document.body;
        if (mainContent) {
            mainContent.style.display = 'none';
        }

        // Create install screen
        const installScreen = document.createElement('div');
        installScreen.id = 'pwa-install-screen';
        installScreen.innerHTML = `
            <div class="install-container">
                <div class="install-content">
                    <div class="app-icon">
                        <img src="/static/images/logo.png" alt="Kickoff Arena" />
                    </div>
                    <h1>Kickoff Arena</h1>
                    <p class="tagline">Professional Tournament Management</p>
                    
                    <div class="install-message">
                        <h2>Install Our App</h2>
                        <p>For the best experience, please install Kickoff Arena as an app on your device.</p>
                    </div>

                    <div class="install-steps">
                        <div class="step">
                            <div class="step-icon">1</div>
                            <div class="step-text">
                                <strong>Tap the share button</strong>
                                <span>Look for <i class="share-icon">⎋</i> in your browser</span>
                            </div>
                        </div>
                        <div class="step">
                            <div class="step-icon">2</div>
                            <div class="step-text">
                                <strong>Add to Home Screen</strong>
                                <span>Select "Add to Home Screen" option</span>
                            </div>
                        </div>
                        <div class="step">
                            <div class="step-icon">3</div>
                            <div class="step-text">
                                <strong>Launch the App</strong>
                                <span>Tap the app icon from your home screen</span>
                            </div>
                        </div>
                    </div>

                    <button id="install-button" class="install-btn hidden">
                        <i class="icon">📱</i>
                        Install App
                    </button>

                    <div class="features-preview">
                        <h3>App Features</h3>
                        <div class="features-grid">
                            <div class="feature">
                                <span class="feature-icon">🏆</span>
                                <span>Create Tournaments</span>
                            </div>
                            <div class="feature">
                                <span class="feature-icon">⚡</span>
                                <span>Live Updates</span>
                            </div>
                            <div class="feature">
                                <span class="feature-icon">📱</span>
                                <span>Offline Access</span>
                            </div>
                            <div class="feature">
                                <span class="feature-icon">🔔</span>
                                <span>Push Notifications</span>
                            </div>
                        </div>
                    </div>

                    <div class="browser-instructions">
                        <details>
                            <summary>Device-specific instructions</summary>
                            <div class="browser-guides">
                                <div class="guide" data-browser="chrome-android">
                                    <h4>Chrome on Android</h4>
                                    <p>1. Tap the menu (⋮) button<br>2. Select "Add to Home screen"<br>3. Tap "Add"</p>
                                </div>
                                <div class="guide" data-browser="safari-ios">
                                    <h4>Safari on iOS</h4>
                                    <p>1. Tap the share button (⎋)<br>2. Select "Add to Home Screen"<br>3. Tap "Add"</p>
                                </div>
                                <div class="guide" data-browser="firefox-android">
                                    <h4>Firefox on Android</h4>
                                    <p>1. Tap the menu (⋮) button<br>2. Select "Install"<br>3. Tap "Add to Home screen"</p>
                                </div>
                            </div>
                        </details>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(installScreen);
        this.setupInstallScreenEvents();
    }

    // Setup install screen events
    setupInstallScreenEvents() {
        const installButton = document.getElementById('install-button');
        if (installButton && this.deferredPrompt) {
            installButton.classList.remove('hidden');
            installButton.addEventListener('click', () => {
                this.triggerInstall();
            });
        }
    }

    // Register service worker
    async registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/static/sw.js');
                console.log('Service Worker registered successfully:', registration);

                // Listen for updates
                registration.addEventListener('updatefound', () => {
                    console.log('Service Worker update found');
                });

                return registration;
            } catch (error) {
                console.error('Service Worker registration failed:', error);
            }
        }
    }

    // Setup install prompt handling
    setupInstallPrompt() {
        window.addEventListener('beforeinstallprompt', (e) => {
            console.log('Install prompt available');
            e.preventDefault();
            this.deferredPrompt = e;
            
            // Show install button if on mobile
            if (this.isMobile) {
                const installButton = document.getElementById('install-button');
                if (installButton) {
                    installButton.classList.remove('hidden');
                    installButton.addEventListener('click', () => {
                        this.triggerInstall();
                    });
                }
            }
        });

        // Listen for successful installation
        window.addEventListener('appinstalled', () => {
            console.log('PWA was installed successfully');
            this.hideInstallScreen();
            this.deferredPrompt = null;
            
            // Reload to show app content
            window.location.reload();
        });
    }

    // Trigger PWA installation
    async triggerInstall() {
        if (!this.deferredPrompt) return;

        try {
            this.deferredPrompt.prompt();
            const result = await this.deferredPrompt.userChoice;
            
            if (result.outcome === 'accepted') {
                console.log('User accepted the install prompt');
            } else {
                console.log('User dismissed the install prompt');
            }
        } catch (error) {
            console.error('Install prompt failed:', error);
        }
        
        this.deferredPrompt = null;
    }

    // Hide install screen
    hideInstallScreen() {
        const installScreen = document.getElementById('pwa-install-screen');
        if (installScreen) {
            installScreen.remove();
        }

        // Show main content
        const mainContent = document.querySelector('main') || document.body;
        if (mainContent) {
            mainContent.style.display = '';
        }
    }

    // Enable mobile optimizations for PWA mode
    enableMobileOptimizations() {
        // Add PWA class to body
        document.body.classList.add('pwa-mode', 'mobile-optimized');

        // Hide browser UI
        this.hideBrowserUI();

        // Setup mobile navigation
        this.setupMobileNavigation();

        // Setup touch optimizations
        this.setupTouchOptimizations();

        // Setup live updates
        this.setupLiveUpdates();
    }

    // Hide browser UI for app-like experience
    hideBrowserUI() {
        // Prevent zoom
        document.addEventListener('gesturestart', (e) => e.preventDefault());
        document.addEventListener('gesturechange', (e) => e.preventDefault());

        // Prevent context menu on long press
        document.addEventListener('contextmenu', (e) => {
            if (this.isPWA) e.preventDefault();
        });

        // Set viewport for app mode
        const viewport = document.querySelector('meta[name=viewport]');
        if (viewport) {
            viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover';
        }
    }

    // Setup mobile navigation
    setupMobileNavigation() {
        // This will be enhanced when we add mobile navigation components
        console.log('Mobile navigation setup');
    }

    // Setup touch optimizations
    setupTouchOptimizations() {
        // Add touch-friendly classes
        document.body.classList.add('touch-optimized');

        // Improve button tap targets
        const buttons = document.querySelectorAll('button, .btn, a[role="button"]');
        buttons.forEach(button => {
            if (!button.classList.contains('touch-optimized')) {
                button.classList.add('touch-optimized');
            }
        });
    }

    // Setup live updates for mobile
    setupLiveUpdates() {
        // Enhanced WebSocket handling for mobile
        if (typeof io !== 'undefined') {
            const socket = io();
            
            // Handle tournament updates
            socket.on('tournament_update', (data) => {
                this.handleTournamentUpdate(data);
            });

            // Handle match updates
            socket.on('match_update', (data) => {
                this.handleMatchUpdate(data);
            });
        }
    }

    // Handle tournament updates
    handleTournamentUpdate(data) {
        console.log('Tournament update received:', data);
        
        // Show notification if app is in background
        if (document.hidden && 'serviceWorker' in navigator) {
            navigator.serviceWorker.ready.then(registration => {
                registration.showNotification('Tournament Update', {
                    body: data.message || 'Tournament has been updated',
                    icon: '/static/images/icon-192x192.png',
                    tag: 'tournament-update'
                });
            });
        }

        // Update UI if specific elements exist
        if (data.tournament_id) {
            const tournamentElement = document.querySelector(`[data-tournament-id="${data.tournament_id}"]`);
            if (tournamentElement) {
                // Refresh tournament data
                this.refreshTournamentData(data.tournament_id);
            }
        }
    }

    // Handle match updates
    handleMatchUpdate(data) {
        console.log('Match update received:', data);
        
        // Update match displays
        if (data.match_id) {
            const matchElement = document.querySelector(`[data-match-id="${data.match_id}"]`);
            if (matchElement) {
                this.updateMatchDisplay(matchElement, data);
            }
        }
    }

    // Refresh tournament data
    refreshTournamentData(tournamentId) {
        // This would trigger a refresh of tournament-specific data
        const event = new CustomEvent('tournamentUpdate', {
            detail: { tournamentId }
        });
        document.dispatchEvent(event);
    }

    // Update match display
    updateMatchDisplay(element, data) {
        // Update match score/status display
        if (data.score) {
            const scoreElement = element.querySelector('.match-score');
            if (scoreElement) {
                scoreElement.textContent = data.score;
            }
        }

        if (data.status) {
            const statusElement = element.querySelector('.match-status');
            if (statusElement) {
                statusElement.textContent = data.status;
                statusElement.className = `match-status status-${data.status.toLowerCase()}`;
            }
        }
    }
}

// Initialize PWA Controller when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.pwaController = new PWAController();
    });
} else {
    window.pwaController = new PWAController();
}
