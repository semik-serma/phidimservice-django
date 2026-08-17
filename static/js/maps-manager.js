/**
 * Phidim Service Platform - Maps & Live Tracking Manager
 * ------------------------------------------------------
 * Supports Google Maps API with auto-fallback to Leaflet/OpenStreetMap.
 * Features custom animated markers, live movement interpolation,
 * route polyline, and distance meter.
 */

class PhidimMapsManager {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.googleApiKey = options.googleApiKey || '';
        this.defaultCenter = options.center || { lat: 27.717245, lng: 85.32396 }; // Kathmandu default
        this.zoom = options.zoom || 14;

        this.mapType = 'none'; // 'google' or 'leaflet'
        this.mapInstance = null;
        
        // Markers & overlays
        this.customerMarker = null;
        this.technicianMarker = null;
        this.routeLine = null;

        // Current coordinates
        this.customerCoords = options.customerCoords || null;
        this.technicianCoords = options.technicianCoords || null;
    }

    /**
     * Initializes the map engine (Google Maps or Leaflet fallback).
     */
    async init() {
        if (!this.container) {
            console.error(`[MapsManager] Container #${this.containerId} not found.`);
            return;
        }

        // Try Google Maps if API key is provided and window.google is loaded or can load
        if (this.googleApiKey && typeof google !== 'undefined' && google.maps) {
            this.initGoogleMap();
        } else if (this.googleApiKey && !window._loadingGoogleMaps) {
            try {
                await this.loadGoogleMapsScript();
                this.initGoogleMap();
            } catch (err) {
                console.warn('[MapsManager] Google Maps load failed, falling back to Leaflet:', err);
                await this.initLeafletFallback();
            }
        } else {
            // Leaflet fallback
            await this.initLeafletFallback();
        }
    }

    loadGoogleMapsScript() {
        return new Promise((resolve, reject) => {
            if (typeof google !== 'undefined' && google.maps) {
                return resolve();
            }
            window._loadingGoogleMaps = true;
            const script = document.createElement('script');
            script.src = `https://maps.googleapis.com/maps/api/js?key=${this.googleApiKey}&libraries=geometry`;
            script.async = true;
            script.defer = true;
            script.onload = () => {
                window._loadingGoogleMaps = false;
                resolve();
            };
            script.onerror = (e) => {
                window._loadingGoogleMaps = false;
                reject(e);
            };
            document.head.appendChild(script);
        });
    }

    initGoogleMap() {
        this.mapType = 'google';
        const center = this.technicianCoords || this.customerCoords || this.defaultCenter;

        const styledMapType = new google.maps.StyledMapType([
            { elementType: "geometry", stylers: [{ color: "#16231c" }] },
            { elementType: "labels.text.stroke", stylers: [{ color: "#121b16" }] },
            { elementType: "labels.text.fill", stylers: [{ color: "#9cbab0" }] },
            { featureType: "road", elementType: "geometry", stylers: [{ color: "#253b30" }] },
            { featureType: "road", elementType: "geometry.stroke", stylers: [{ color: "#1a2c23" }] },
            { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#ff5400" }, { weight: 1.2 }] },
            { featureType: "water", elementType: "geometry", stylers: [{ color: "#0c1511" }] },
            { featureType: "poi", elementType: "labels", stylers: [{ visibility: "off" }] }
        ], { name: "Phidim Dark" });

        this.mapInstance = new google.maps.Map(this.container, {
            center: { lat: parseFloat(center.lat || center.latitude), lng: parseFloat(center.lng || center.longitude) },
            zoom: this.zoom,
            disableDefaultUI: false,
            zoomControl: true,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: true,
            mapTypeControlOptions: {
                mapTypeIds: ["roadmap", "satellite", "phidim_style"]
            }
        });

        this.mapInstance.mapTypes.set("phidim_style", styledMapType);
        this.mapInstance.setMapTypeId("phidim_style");

        console.log('[MapsManager] Initialized Google Maps Engine');
        this.renderAllMarkers();
    }

    async initLeafletFallback() {
        this.mapType = 'leaflet';
        
        // Ensure Leaflet CSS & JS are loaded
        await this.ensureLeafletLoaded();

        const center = this.technicianCoords || this.customerCoords || this.defaultCenter;
        const lat = parseFloat(center.lat || center.latitude);
        const lng = parseFloat(center.lng || center.longitude);

        if (this.mapInstance && this.mapInstance.remove) {
            this.mapInstance.remove();
        }

        this.mapInstance = L.map(this.containerId, {
            zoomControl: true,
            attributionControl: false
        }).setView([lat, lng], this.zoom);

        // Add high-contrast Dark Carto/OSM tile layer matching platform design
        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            maxZoom: 19,
            subdomains: 'abcd'
        }).addTo(this.mapInstance);

        console.log('[MapsManager] Initialized Leaflet OpenStreetMap Engine');
        this.renderAllMarkers();
    }

    ensureLeafletLoaded() {
        return new Promise((resolve) => {
            if (window.L) return resolve();

            // Inject CSS
            if (!document.getElementById('leaflet-css')) {
                const link = document.createElement('link');
                link.id = 'leaflet-css';
                link.rel = 'stylesheet';
                link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
                document.head.appendChild(link);
            }

            // Inject JS
            if (!document.getElementById('leaflet-js')) {
                const script = document.createElement('script');
                script.id = 'leaflet-js';
                script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
                script.onload = () => resolve();
                document.head.appendChild(script);
            } else {
                resolve();
            }
        });
    }

    /**
     * Render / Update both Customer and Technician markers.
     */
    renderAllMarkers() {
        if (this.customerCoords) {
            this.updateCustomerMarker(this.customerCoords);
        }
        if (this.technicianCoords) {
            this.updateTechnicianMarker(this.technicianCoords);
        }
        this.updateRouteAndBounds();
    }

    /**
     * Update or create Customer Location Marker.
     */
    updateCustomerMarker(coords) {
        if (!coords || !coords.lat && !coords.latitude) return;
        const lat = parseFloat(coords.lat || coords.latitude);
        const lng = parseFloat(coords.lng || coords.longitude);
        this.customerCoords = { lat, lng };

        if (this.mapType === 'google') {
            if (!this.customerMarker) {
                const iconSvg = {
                    url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(`
                        <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
                            <circle cx="20" cy="20" r="18" fill="#ff5400" fill-opacity="0.25"/>
                            <circle cx="20" cy="20" r="12" fill="#ff5400" stroke="#ffffff" stroke-width="2.5"/>
                            <circle cx="20" cy="20" r="4" fill="#ffffff"/>
                        </svg>
                    `),
                    scaledSize: new google.maps.Size(40, 40),
                    anchor: new google.maps.Point(20, 20)
                };

                this.customerMarker = new google.maps.Marker({
                    position: { lat, lng },
                    map: this.mapInstance,
                    title: 'Customer Service Location',
                    icon: iconSvg
                });
            } else {
                this.customerMarker.setPosition({ lat, lng });
            }
        } else if (this.mapType === 'leaflet' && window.L) {
            const customerIcon = L.divIcon({
                className: 'custom-map-pin customer-pin',
                html: `
                    <div style="position:relative; width:34px; height:34px; background:#ff5400; border:2.5px solid #fff; border-radius:50%; display:flex; align-items:center; justify-content:center; box-shadow:0 0 16px rgba(255,84,0,0.6); color:#fff; font-size:14px;">
                        <i class="fa-solid fa-house-chimney"></i>
                    </div>
                `,
                iconSize: [34, 34],
                iconAnchor: [17, 17]
            });

            if (!this.customerMarker) {
                this.customerMarker = L.marker([lat, lng], { icon: customerIcon }).addTo(this.mapInstance);
                this.customerMarker.bindPopup("<b>Service Location</b><br>Customer Request Point");
            } else {
                this.customerMarker.setLatLng([lat, lng]);
            }
        }
    }

    /**
     * Update or create Technician Moving Marker with animation.
     */
    updateTechnicianMarker(coords) {
        if (!coords || !coords.lat && !coords.latitude) return;
        const lat = parseFloat(coords.lat || coords.latitude);
        const lng = parseFloat(coords.lng || coords.longitude);
        this.technicianCoords = { lat, lng };

        if (this.mapType === 'google') {
            if (!this.technicianMarker) {
                const techIcon = {
                    url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(`
                        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">
                            <circle cx="24" cy="24" r="22" fill="#122b20" stroke="#ff5400" stroke-width="3"/>
                            <circle cx="24" cy="24" r="14" fill="#ff5400"/>
                            <path d="M22 17h4v14h-4z M17 22h14v4h-14z" fill="#ffffff" transform="rotate(45 24 24)"/>
                        </svg>
                    `),
                    scaledSize: new google.maps.Size(48, 48),
                    anchor: new google.maps.Point(24, 24)
                };

                this.technicianMarker = new google.maps.Marker({
                    position: { lat, lng },
                    map: this.mapInstance,
                    title: 'Technician Location (Live GPS)',
                    icon: techIcon
                });
            } else {
                this.technicianMarker.setPosition({ lat, lng });
            }
        } else if (this.mapType === 'leaflet' && window.L) {
            const techIcon = L.divIcon({
                className: 'custom-map-pin technician-pin',
                html: `
                    <div style="position:relative; width:40px; height:40px; background:#122b20; border:2.5px solid #ff5400; border-radius:50%; display:flex; align-items:center; justify-content:center; box-shadow:0 0 20px rgba(255,84,0,0.7); color:#ff5400; font-size:16px; animation: pulseGlow 2s infinite;">
                        <i class="fa-solid fa-wrench"></i>
                    </div>
                `,
                iconSize: [40, 40],
                iconAnchor: [20, 20]
            });

            if (!this.technicianMarker) {
                this.technicianMarker = L.marker([lat, lng], { icon: techIcon }).addTo(this.mapInstance);
                this.technicianMarker.bindPopup("<b>Technician</b><br>Live GPS En Route");
            } else {
                this.technicianMarker.setLatLng([lat, lng]);
            }
        }

        this.updateRouteAndBounds();
    }

    /**
     * Draw / update polyline route line between Customer and Technician and fit map bounds.
     */
    updateRouteAndBounds() {
        if (!this.customerCoords || !this.technicianCoords || !this.mapInstance) return;

        const p1 = [this.customerCoords.lat, this.customerCoords.lng];
        const p2 = [this.technicianCoords.lat, this.technicianCoords.lng];

        if (this.mapType === 'google') {
            const path = [
                { lat: p1[0], lng: p1[1] },
                { lat: p2[0], lng: p2[1] }
            ];

            if (!this.routeLine) {
                this.routeLine = new google.maps.Polyline({
                    path: path,
                    geodesic: true,
                    strokeColor: "#ff5400",
                    strokeOpacity: 0.8,
                    strokeWeight: 3.5,
                    map: this.mapInstance
                });
            } else {
                this.routeLine.setPath(path);
            }

            const bounds = new google.maps.LatLngBounds();
            bounds.extend(path[0]);
            bounds.extend(path[1]);
            this.mapInstance.fitBounds(bounds, 60);

        } else if (this.mapType === 'leaflet' && window.L) {
            if (!this.routeLine) {
                this.routeLine = L.polyline([p1, p2], {
                    color: '#ff5400',
                    weight: 3.5,
                    opacity: 0.85,
                    dashArray: '6, 8'
                }).addTo(this.mapInstance);
            } else {
                this.routeLine.setLatLngs([p1, p2]);
            }

            const bounds = L.latLngBounds([p1, p2]);
            this.mapInstance.fitBounds(bounds, { padding: [50, 50] });
        }
    }
}

window.PhidimMapsManager = PhidimMapsManager;
