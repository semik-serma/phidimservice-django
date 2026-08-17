/**
 * Phidim Service Platform - Real-time Location Tracker
 * ----------------------------------------------------
 * High-precision browser GPS acquisition, permission handling,
 * throttling (every 2-3 seconds), Socket.IO emission, and backend REST persistence.
 */

class LocationTracker {
    constructor(options = {}) {
        this.socket = options.socket || null;
        this.csrfToken = options.csrfToken || '';
        this.userRole = options.userRole || 'customer';
        this.userId = options.userId || null;
        this.currentRequestId = options.currentRequestId || null;
        
        this.watchId = null;
        this.currentPosition = null;
        this.lastSentTime = 0;
        this.throttleIntervalMs = options.throttleIntervalMs || 2500; // 2.5s rate-limit
        this.isTracking = false;
        
        this.onLocationUpdateCallbacks = [];
        this.onErrorCallbacks = [];
        this.onPermissionChangeCallbacks = [];
    }

    /**
     * Request GPS Permission and obtain current fix.
     */
    async requestPermissionAndGetLocation() {
        return new Promise((resolve, reject) => {
            if (!('geolocation' in navigator)) {
                const err = new Error('Geolocation is not supported by your browser.');
                this.notifyError(err);
                return reject(err);
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.handlePositionUpdate(position);
                    this.notifyPermission('granted');
                    resolve(position.coords);
                },
                (error) => {
                    let msg = 'Unable to retrieve your location.';
                    if (error.code === error.PERMISSION_DENIED) {
                        msg = 'Location permission was denied. Please allow location access in your browser settings to enable live tracking.';
                        this.notifyPermission('denied');
                    } else if (error.code === error.POSITION_UNAVAILABLE) {
                        msg = 'Location information is currently unavailable.';
                    } else if (error.code === error.TIMEOUT) {
                        msg = 'Location request timed out.';
                    }
                    const customErr = new Error(msg);
                    this.notifyError(customErr);
                    reject(customErr);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        });
    }

    /**
     * Start continuous background GPS watching (typically for on-duty Technicians).
     */
    startWatching(requestId = null) {
        if (requestId) this.currentRequestId = requestId;
        if (this.isTracking) return;

        if (!('geolocation' in navigator)) {
            this.notifyError(new Error('Geolocation not supported.'));
            return;
        }

        this.isTracking = true;
        this.watchId = navigator.geolocation.watchPosition(
            (position) => this.handlePositionUpdate(position),
            (error) => this.notifyError(error),
            {
                enableHighAccuracy: true,
                maximumAge: 1000,
                timeout: 8000
            }
        );

        console.log(`[LocationTracker] Started tracking GPS (Request ID: ${this.currentRequestId || 'Global'})`);
    }

    /**
     * Stop watching GPS coordinates.
     */
    stopWatching() {
        if (this.watchId !== null) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
        }
        this.isTracking = false;
        console.log('[LocationTracker] Stopped GPS tracking');
    }

    /**
     * Internal handler for incoming browser position updates.
     */
    handlePositionUpdate(position) {
        const coords = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            heading: position.coords.heading,
            speed: position.coords.speed,
            timestamp: position.timestamp
        };

        this.currentPosition = coords;
        this.notifyCallbacks(coords);

        const now = Date.now();
        if (now - this.lastSentTime >= this.throttleIntervalMs) {
            this.lastSentTime = now;
            this.broadcastCoordinates(coords);
            this.persistCoordinatesBackend(coords);
        }
    }

    /**
     * Emit position through Socket.IO for instant room delivery.
     */
    broadcastCoordinates(coords) {
        if (!this.socket || !this.socket.connected) return;

        if (this.userRole === 'technician' && this.currentRequestId) {
            this.socket.emit('technician-location-update', {
                requestId: this.currentRequestId,
                technicianId: this.userId,
                latitude: coords.latitude,
                longitude: coords.longitude,
                accuracy: coords.accuracy,
                heading: coords.heading,
                speed: coords.speed
            });
        }
    }

    /**
     * Persist position to Django database asynchronously.
     */
    async persistCoordinatesBackend(coords) {
        try {
            await fetch('/api/location/update/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    latitude: coords.latitude,
                    longitude: coords.longitude,
                    accuracy: coords.accuracy
                })
            });
        } catch (e) {
            // Silently swallow background sync network hiccups
            console.warn('[LocationTracker] Backend location sync error:', e);
        }
    }

    // Callbacks management
    onLocationUpdate(fn) { this.onLocationUpdateCallbacks.push(fn); }
    onError(fn) { this.onErrorCallbacks.push(fn); }
    onPermissionChange(fn) { this.onPermissionChangeCallbacks.push(fn); }

    notifyCallbacks(coords) {
        this.onLocationUpdateCallbacks.forEach(fn => {
            try { fn(coords); } catch (e) { console.error(e); }
        });
    }

    notifyError(err) {
        this.onErrorCallbacks.forEach(fn => {
            try { fn(err); } catch (e) { console.error(e); }
        });
    }

    notifyPermission(status) {
        this.onPermissionChangeCallbacks.forEach(fn => {
            try { fn(status); } catch (e) { console.error(e); }
        });
    }
}

window.LocationTracker = LocationTracker;
