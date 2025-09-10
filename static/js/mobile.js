// Mobile JavaScript for Enhanced Touch Interactions
class MobileInteractions {
    constructor() {
        this.touchStartY = 0;
        this.touchEndY = 0;
        this.isRefreshing = false;
        this.refreshThreshold = 80;
        
        this.init();
    }

    init() {
        if (!this.isMobile()) return;
        
        console.log('Initializing mobile interactions');
        
        // Setup touch gestures
        this.setupPullToRefresh();
        this.setupSwipeGestures();
        this.setupTouchOptimizations();
        this.setupMobileNavigation();
        
        // Setup mobile-specific event listeners
        this.setupMobileEvents();
    }

    isMobile() {
        return /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
               window.innerWidth <= 768;
    }

    // Pull to refresh functionality
    setupPullToRefresh() {
        let startY = 0;
        let currentY = 0;
        let pulling = false;
        let pullIndicator = null;

        const createPullIndicator = () => {
            if (pullIndicator) return pullIndicator;
            
            pullIndicator = document.createElement('div');
            pullIndicator.className = 'pull-to-refresh';
            pullIndicator.innerHTML = '<i class="fas fa-arrow-down"></i>';
            document.body.appendChild(pullIndicator);
            return pullIndicator;
        };

        const removePullIndicator = () => {
            if (pullIndicator) {
                pullIndicator.remove();
                pullIndicator = null;
            }
        };

        document.addEventListener('touchstart', (e) => {
            if (window.scrollY <= 0) {
                startY = e.touches[0].pageY;
                pulling = false;
            }
        }, { passive: true });

        document.addEventListener('touchmove', (e) => {
            if (window.scrollY <= 0 && startY > 0) {
                currentY = e.touches[0].pageY;
                const pullDistance = currentY - startY;

                if (pullDistance > 20 && !this.isRefreshing) {
                    pulling = true;
                    const indicator = createPullIndicator();
                    
                    if (pullDistance > this.refreshThreshold) {
                        indicator.classList.add('active');
                        indicator.innerHTML = '<i class="fas fa-sync-alt"></i>';
                    } else {
                        indicator.classList.remove('active');
                        indicator.innerHTML = '<i class="fas fa-arrow-down"></i>';
                    }
                    
                    // Prevent default scroll behavior when pulling
                    e.preventDefault();
                }
            }
        }, { passive: false });

        document.addEventListener('touchend', (e) => {
            if (pulling && !this.isRefreshing) {
                const pullDistance = currentY - startY;
                
                if (pullDistance > this.refreshThreshold) {
                    this.triggerRefresh();
                } else {
                    removePullIndicator();
                }
            }
            
            startY = 0;
            pulling = false;
        }, { passive: true });
    }

    triggerRefresh() {
        if (this.isRefreshing) return;
        
        this.isRefreshing = true;
        const indicator = document.querySelector('.pull-to-refresh');
        
        if (indicator) {
            indicator.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i>';
            indicator.classList.add('active');
        }

        // Show toast notification
        this.showMobileToast('Refreshing tournament data...', 'info');

        // Simulate refresh (replace with actual refresh logic)
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }

    // Swipe gesture handling
    setupSwipeGestures() {
        let startX = 0;
        let startY = 0;
        let endX = 0;
        let endY = 0;

        document.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        }, { passive: true });

        document.addEventListener('touchend', (e) => {
            endX = e.changedTouches[0].clientX;
            endY = e.changedTouches[0].clientY;
            
            this.handleSwipe(startX, startY, endX, endY);
        }, { passive: true });
    }

    handleSwipe(startX, startY, endX, endY) {
        const deltaX = endX - startX;
        const deltaY = endY - startY;
        const minSwipeDistance = 100;

        // Horizontal swipe
        if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
            if (deltaX > 0) {
                this.handleSwipeRight();
            } else {
                this.handleSwipeLeft();
            }
        }
        // Vertical swipe
        else if (Math.abs(deltaY) > Math.abs(deltaX) && Math.abs(deltaY) > minSwipeDistance) {
            if (deltaY > 0) {
                this.handleSwipeDown();
            } else {
                this.handleSwipeUp();
            }
        }
    }

    handleSwipeLeft() {
        // Navigate to next section if applicable
        const nextButton = document.querySelector('.next-section, .nav-next');
        if (nextButton) {
            nextButton.click();
        }
    }

    handleSwipeRight() {
        // Navigate to previous section or go back
        const prevButton = document.querySelector('.prev-section, .nav-prev');
        if (prevButton) {
            prevButton.click();
        } else if (window.history.length > 1) {
            window.history.back();
        }
    }

    handleSwipeUp() {
        // Show mobile navigation or scroll to top
        const mobileNav = document.querySelector('.mobile-bottom-nav');
        if (mobileNav) {
            mobileNav.style.transform = 'translateY(0)';
        }
    }

    handleSwipeDown() {
        // Hide mobile navigation
        const mobileNav = document.querySelector('.mobile-bottom-nav');
        if (mobileNav) {
            mobileNav.style.transform = 'translateY(100%)';
        }
    }

    // Touch optimizations
    setupTouchOptimizations() {
        // Improve button touch targets
        const buttons = document.querySelectorAll('button, .btn, a[role="button"], input[type="submit"]');
        buttons.forEach(button => {
            if (!button.classList.contains('touch-optimized')) {
                button.classList.add('touch-optimized');
            }
        });

        // Add touch feedback
        document.addEventListener('touchstart', (e) => {
            const target = e.target.closest('button, .btn, a, input[type="submit"]');
            if (target) {
                target.style.transform = 'scale(0.98)';
                target.style.opacity = '0.8';
            }
        }, { passive: true });

        document.addEventListener('touchend', (e) => {
            const target = e.target.closest('button, .btn, a, input[type="submit"]');
            if (target) {
                setTimeout(() => {
                    target.style.transform = '';
                    target.style.opacity = '';
                }, 100);
            }
        }, { passive: true });

        // Prevent double-tap zoom on buttons
        let lastTouchEnd = 0;
        document.addEventListener('touchend', (e) => {
            const now = new Date().getTime();
            if (now - lastTouchEnd <= 300) {
                e.preventDefault();
            }
            lastTouchEnd = now;
        }, false);
    }

    // Mobile navigation setup
    setupMobileNavigation() {
        // Create mobile bottom navigation if it doesn't exist
        if (!document.querySelector('.mobile-bottom-nav')) {
            this.createMobileBottomNav();
        }

        // Setup mobile menu toggle
        this.setupMobileMenuToggle();
    }

    createMobileBottomNav() {
        const currentPath = window.location.pathname;
        const nav = document.createElement('nav');
        nav.className = 'mobile-bottom-nav';
        
        const navItems = [
            { icon: 'fas fa-home', label: 'Home', url: '/', active: currentPath === '/' },
            { icon: 'fas fa-trophy', label: 'Tournaments', url: '/explore', active: currentPath.startsWith('/explore') },
            { icon: 'fas fa-plus-circle', label: 'Create', url: '/tournament/create', active: currentPath.startsWith('/tournament/create') },
            { icon: 'fas fa-user', label: 'Profile', url: '/dashboard', active: currentPath.startsWith('/dashboard') }
        ];

        nav.innerHTML = navItems.map(item => `
            <a href="${item.url}" class="bottom-nav-item ${item.active ? 'active' : ''}">
                <i class="${item.icon}"></i>
                <span>${item.label}</span>
            </a>
        `).join('');

        document.body.appendChild(nav);
    }

    setupMobileMenuToggle() {
        const hamburgerButton = document.querySelector('[data-toggle="mobile-menu"]');
        if (hamburgerButton) {
            hamburgerButton.addEventListener('click', () => {
                const mobileMenu = document.querySelector('.mobile-menu');
                if (mobileMenu) {
                    mobileMenu.classList.toggle('show');
                }
            });
        }
    }

    // Mobile events setup
    setupMobileEvents() {
        // Handle orientation changes
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.handleOrientationChange();
            }, 100);
        });

        // Handle app state changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.handleAppBackground();
            } else {
                this.handleAppForeground();
            }
        });

        // Handle network changes
        window.addEventListener('online', () => {
            this.handleNetworkOnline();
        });

        window.addEventListener('offline', () => {
            this.handleNetworkOffline();
        });
    }

    handleOrientationChange() {
        // Refresh layout after orientation change
        window.dispatchEvent(new Event('resize'));
    }

    handleAppBackground() {
        // App went to background - pause heavy operations
        console.log('App backgrounded');
    }

    handleAppForeground() {
        // App returned to foreground - resume operations
        console.log('App foregrounded');
        
        // Check for updates
        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({ type: 'CHECK_FOR_UPDATES' });
        }
    }

    handleNetworkOnline() {
        this.showMobileToast('Connection restored', 'success');
        
        // Sync any pending data
        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({ type: 'SYNC_DATA' });
        }
    }

    handleNetworkOffline() {
        this.showMobileToast('You are offline. Some features may not be available.', 'warning');
    }

    // Mobile toast notifications
    showMobileToast(message, type = 'info', duration = 3000) {
        // Remove any existing toasts
        const existingToast = document.querySelector('.mobile-toast');
        if (existingToast) {
            existingToast.remove();
        }

        // Create new toast
        const toast = document.createElement('div');
        toast.className = `mobile-toast ${type}`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // Show toast
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        // Hide toast after duration
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, duration);
    }

    // Utility methods
    vibrate(pattern = [200, 100, 200]) {
        if ('vibrate' in navigator) {
            navigator.vibrate(pattern);
        }
    }

    hapticFeedback(type = 'light') {
        // iOS Haptic Feedback
        if (window.DeviceMotionEvent && typeof DeviceMotionEvent.requestPermission === 'function') {
            this.vibrate([10]);
        }
        // Android Haptic Feedback
        else if ('vibrate' in navigator) {
            const patterns = {
                light: [50],
                medium: [100],
                heavy: [200]
            };
            this.vibrate(patterns[type] || patterns.light);
        }
    }
}

// Initialize mobile interactions when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.mobileInteractions = new MobileInteractions();
    });
} else {
    window.mobileInteractions = new MobileInteractions();
}

// Export for use in other scripts
window.MobileInteractions = MobileInteractions;
