// Service Worker for Kickoff Arena PWA
const CACHE_NAME = 'kickoff-arena-v1';
const OFFLINE_URL = '/offline';

// Assets to cache for offline functionality
const CACHE_ASSETS = [
    '/',
    '/static/manifest.json',
    '/static/css/mobile.css',
    '/static/js/mobile.js',
    '/static/js/pwa-detection.js',
    '/static/images/logo.png',
    '/static/images/icon-192x192.png',
    '/static/images/icon-512x512.png',
    '/explore',
    '/offline'
];

// Install event - cache essential assets
self.addEventListener('install', event => {
    console.log('Service Worker: Install event');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Service Worker: Caching assets');
                return cache.addAll(CACHE_ASSETS).catch(err => {
                    console.warn('Service Worker: Some assets failed to cache', err);
                    // Cache essential assets individually
                    return Promise.allSettled([
                        cache.add('/'),
                        cache.add('/static/manifest.json'),
                        cache.add('/explore')
                    ]);
                });
            })
            .then(() => self.skipWaiting())
            .catch(err => console.error('Service Worker: Cache failed', err))
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Service Worker: Activate event');
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cache => {
                        if (cache !== CACHE_NAME) {
                            console.log('Service Worker: Deleting old cache', cache);
                            return caches.delete(cache);
                        }
                    })
                );
            })
            .then(() => self.clients.claim())
    );
});

// Fetch event - serve cached content when offline
self.addEventListener('fetch', event => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;
    
    // Skip external requests
    if (!event.request.url.startsWith(self.location.origin)) return;

    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Return cached version if available
                if (response) {
                    return response;
                }
                
                // Otherwise fetch from network
                return fetch(event.request)
                    .then(response => {
                        // Don't cache error responses
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }

                        // Cache successful responses for API endpoints and pages
                        if (event.request.url.includes('/api/') || 
                            event.request.url.includes('/tournament/') ||
                            event.request.url.includes('/dashboard')) {
                            
                            const responseToCache = response.clone();
                            caches.open(CACHE_NAME)
                                .then(cache => {
                                    cache.put(event.request, responseToCache);
                                })
                                .catch(err => console.warn('Failed to cache response', err));
                        }

                        return response;
                    })
                    .catch(() => {
                        // Show offline page for navigation requests when network fails
                        if (event.request.mode === 'navigate') {
                            return caches.match('/') || new Response('Offline - Please check your internet connection');
                        }
                    });
            })
    );
});

// Background sync for tournament updates
self.addEventListener('sync', event => {
    if (event.tag === 'tournament-update') {
        event.waitUntil(syncTournamentData());
    }
});

// Push notifications for tournament updates
self.addEventListener('push', event => {
    if (!event.data) return;

    const data = event.data.json();
    const options = {
        body: data.body || 'Tournament update available',
        icon: '/static/images/icon-192x192.png',
        badge: '/static/images/icon-72x72.png',
        data: data.url || '/',
        actions: [
            {
                action: 'view',
                title: 'View Tournament',
                icon: '/static/images/icon-96x96.png'
            },
            {
                action: 'dismiss',
                title: 'Dismiss'
            }
        ],
        vibrate: [200, 100, 200],
        tag: 'tournament-update',
        renotify: true
    };

    event.waitUntil(
        self.registration.showNotification(data.title || 'Kickoff Arena', options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    event.notification.close();

    if (event.action === 'view') {
        const urlToOpen = event.notification.data || '/';
        event.waitUntil(
            clients.matchAll({ type: 'window', includeUncontrolled: true })
                .then(clientList => {
                    // Check if app is already open
                    for (const client of clientList) {
                        if (client.url.includes(self.location.origin) && 'focus' in client) {
                            client.navigate(urlToOpen);
                            return client.focus();
                        }
                    }
                    
                    // Open new window if app not already open
                    if (clients.openWindow) {
                        return clients.openWindow(urlToOpen);
                    }
                })
        );
    }
});

// Sync tournament data in background
async function syncTournamentData() {
    try {
        // Get cached tournament data
        const cache = await caches.open(CACHE_NAME);
        const tournamentRequests = await cache.keys();
        
        // Update tournament data from server
        const updatePromises = tournamentRequests
            .filter(request => request.url.includes('/tournament/'))
            .map(async (request) => {
                try {
                    const response = await fetch(request.url);
                    if (response.ok) {
                        await cache.put(request, response.clone());
                    }
                } catch (error) {
                    console.log('Failed to sync:', request.url);
                }
            });
            
        await Promise.allSettled(updatePromises);
        console.log('Tournament data synced successfully');
    } catch (error) {
        console.error('Background sync failed:', error);
    }
}
