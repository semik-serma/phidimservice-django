/**
 * Phidim Service Platform - WebRTC Video Calling Engine
 * -----------------------------------------------------
 * High-performance peer-to-peer audio/video calling using Socket.IO signaling.
 * Features Web Audio tone synthesis, screen sharing, media toggling,
 * floating in-dashboard modal, and state management.
 */

class PhidimVideoCall {
    constructor(options = {}) {
        this.socket = options.socket || null;
        this.userId = options.userId || null;
        this.userName = options.userName || 'User';
        this.userAvatar = options.userAvatar || '';
        this.userRole = options.userRole || 'customer';

        this.peerConnection = null;
        this.localStream = null;
        this.remoteStream = null;
        this.screenStream = null;

        this.activeRoomId = null;
        this.activeRequestId = null;
        this.targetUserId = null;
        this.callState = 'idle'; // idle | calling | ringing | connecting | connected | ended

        this.isAudioMuted = false;
        this.isVideoMuted = false;
        this.isScreenSharing = false;

        this.rtcConfig = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' },
                { urls: 'stun:stun2.l.google.com:19302' }
            ]
        };

        this.audioCtx = null;
        this.ringtoneInterval = null;

        this.initElements();
        this.bindSocketEvents();
    }

    initElements() {
        this.modal = document.getElementById('videoCallModal');
        this.localVideo = document.getElementById('localVideoElement');
        this.remoteVideo = document.getElementById('remoteVideoElement');
        this.statusText = document.getElementById('callStatusIndicator');
        this.partnerNameElem = document.getElementById('callPartnerName');
        this.partnerAvatarElem = document.getElementById('callPartnerAvatar');
        this.incomingModal = document.getElementById('incomingCallModal');
        this.callerNameElem = document.getElementById('incomingCallerName');
        this.callerServiceElem = document.getElementById('incomingServiceTitle');
    }

    bindSocketEvents() {
        if (!this.socket) return;

        // 1. Incoming Call Alert
        this.socket.on('incoming-call', (data) => {
            console.log('[VideoCall] Incoming call received:', data);
            this.handleIncomingCall(data);
        });

        // 2. Call Accepted by Receiver
        this.socket.on('call-accepted', async (data) => {
            console.log('[VideoCall] Call accepted by peer:', data);
            this.stopRingtone();
            this.setCallState('connecting');
            await this.createAndSendOffer();
        });

        // 3. Call Rejected
        this.socket.on('call-rejected', (data) => {
            console.log('[VideoCall] Call rejected:', data);
            this.stopRingtone();
            this.setCallState('ended', data.reason || 'Call was declined.');
            setTimeout(() => this.closeCallModal(), 2500);
        });

        // 4. Call Ended
        this.socket.on('call-ended', () => {
            console.log('[VideoCall] Peer ended call');
            this.endCall(false);
        });

        // 5. WebRTC Offer
        this.socket.on('webrtc-offer', async ({ offer }) => {
            console.log('[VideoCall] Received WebRTC offer');
            await this.handleReceivedOffer(offer);
        });

        // 6. WebRTC Answer
        this.socket.on('webrtc-answer', async ({ answer }) => {
            console.log('[VideoCall] Received WebRTC answer');
            await this.handleReceivedAnswer(answer);
        });

        // 7. WebRTC ICE Candidate
        this.socket.on('webrtc-ice-candidate', async ({ candidate }) => {
            if (this.peerConnection && candidate) {
                try {
                    await this.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
                } catch (e) {
                    console.error('[VideoCall] Error adding ICE candidate:', e);
                }
            }
        });
    }

    /**
     * Start Outgoing Call to a technician or customer on an active request.
     */
    async startCall({ targetUserId, requestId, roomId, targetName, targetAvatar, serviceTitle }) {
        this.targetUserId = targetUserId;
        this.activeRequestId = requestId;
        this.activeRoomId = roomId;

        if (this.partnerNameElem) this.partnerNameElem.innerText = targetName || 'Specialist';
        if (this.partnerAvatarElem && targetAvatar) this.partnerAvatarElem.src = targetAvatar;

        this.openCallModal();
        this.setCallState('calling', `Calling ${targetName || 'technician'}...`);
        this.playRingtone('outgoing');

        try {
            await this.setupLocalMedia();
            this.setupPeerConnection();

            // Emit initiation to socket signaling server
            this.socket.emit('call-user', {
                targetUserId,
                requestId,
                roomId,
                callerName: this.userName,
                callerAvatar: this.userAvatar,
                serviceTitle
            });
        } catch (err) {
            console.error('[VideoCall] Media setup failed:', err);
            this.setCallState('ended', 'Could not access camera/microphone. Please allow media permissions.');
            this.stopRingtone();
        }
    }

    /**
     * Display Incoming Call banner/modal.
     */
    handleIncomingCall(data) {
        this.pendingCallData = data;
        this.activeRoomId = data.roomId;
        this.activeRequestId = data.requestId;
        this.targetUserId = data.callerId;

        if (this.callerNameElem) this.callerNameElem.innerText = data.callerName || 'Phidim User';
        if (this.callerServiceElem) this.callerServiceElem.innerText = data.serviceTitle || 'Active Service Call';

        if (this.incomingModal) {
            this.incomingModal.style.display = 'flex';
        }

        this.playRingtone('incoming');
    }

    /**
     * Receiver clicks Accept Call.
     */
    async acceptIncomingCall() {
        this.stopRingtone();
        if (this.incomingModal) this.incomingModal.style.display = 'none';

        if (!this.pendingCallData) return;

        if (this.partnerNameElem) this.partnerNameElem.innerText = this.pendingCallData.callerName || 'Caller';
        this.openCallModal();
        this.setCallState('connecting', 'Connecting audio & video stream...');

        try {
            await this.setupLocalMedia();
            this.setupPeerConnection();

            this.socket.emit('accept-call', {
                roomId: this.activeRoomId,
                callerSocketId: this.pendingCallData.callerSocketId
            });
        } catch (err) {
            console.error('[VideoCall] Media error on accept:', err);
            this.setCallState('ended', 'Failed to initialize local media devices.');
        }
    }

    /**
     * Receiver clicks Reject Call.
     */
    rejectIncomingCall() {
        this.stopRingtone();
        if (this.incomingModal) this.incomingModal.style.display = 'none';

        if (this.pendingCallData) {
            this.socket.emit('reject-call', {
                roomId: this.pendingCallData.roomId,
                callerSocketId: this.pendingCallData.callerSocketId,
                reason: 'Recipient is currently unavailable'
            });
            this.pendingCallData = null;
        }
    }

    /**
     * Acquire User Camera & Microphone.
     */
    async setupLocalMedia() {
        this.localStream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 1280 }, height: { ideal: 720 } },
            audio: { echoCancellation: true, noiseSuppression: true }
        });

        if (this.localVideo) {
            this.localVideo.srcObject = this.localStream;
            this.localVideo.muted = true; // Avoid local audio feedback
        }
    }

    /**
     * Instantiate RTCPeerConnection and bind tracks.
     */
    setupPeerConnection() {
        this.peerConnection = new RTCPeerConnection(this.rtcConfig);

        // Add local tracks to peer connection
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => {
                this.peerConnection.addTrack(track, this.localStream);
            });
        }

        // Handle remote incoming tracks
        this.peerConnection.ontrack = (event) => {
            console.log('[VideoCall] Received remote stream track:', event.track.kind);
            if (!this.remoteStream) {
                this.remoteStream = new MediaStream();
                if (this.remoteVideo) {
                    this.remoteVideo.srcObject = this.remoteStream;
                }
            }
            this.remoteStream.addTrack(event.track);
            this.setCallState('connected', 'Connected');
        };

        // ICE Candidate discovery
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate && this.activeRoomId) {
                this.socket.emit('webrtc-ice-candidate', {
                    roomId: this.activeRoomId,
                    candidate: event.candidate
                });
            }
        };

        // Connection state changes
        this.peerConnection.onconnectionstatechange = () => {
            console.log('[VideoCall] Peer connection state:', this.peerConnection.connectionState);
            if (this.peerConnection.connectionState === 'connected') {
                this.setCallState('connected', 'Connected');
            } else if (this.peerConnection.connectionState === 'disconnected' || this.peerConnection.connectionState === 'failed') {
                this.setCallState('ended', 'Connection lost.');
            }
        };
    }

    async createAndSendOffer() {
        if (!this.peerConnection) return;
        const offer = await this.peerConnection.createOffer();
        await this.peerConnection.setLocalDescription(offer);

        this.socket.emit('webrtc-offer', {
            roomId: this.activeRoomId,
            offer: offer
        });
    }

    async handleReceivedOffer(offer) {
        if (!this.peerConnection) {
            await this.setupLocalMedia();
            this.setupPeerConnection();
        }

        await this.peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
        const answer = await this.peerConnection.createAnswer();
        await this.peerConnection.setLocalDescription(answer);

        this.socket.emit('webrtc-answer', {
            roomId: this.activeRoomId,
            answer: answer
        });
    }

    async handleReceivedAnswer(answer) {
        if (this.peerConnection) {
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
        }
    }

    /**
     * Toggle Local Microphone Mute.
     */
    toggleAudio() {
        if (!this.localStream) return;
        this.isAudioMuted = !this.isAudioMuted;
        this.localStream.getAudioTracks().forEach(track => {
            track.enabled = !this.isAudioMuted;
        });

        const micBtn = document.getElementById('btnToggleMic');
        if (micBtn) {
            micBtn.classList.toggle('active-muted', this.isAudioMuted);
            micBtn.innerHTML = this.isAudioMuted ? '<i class="fa-solid fa-microphone-slash"></i>' : '<i class="fa-solid fa-microphone"></i>';
        }
    }

    /**
     * Toggle Local Camera Off/On.
     */
    toggleVideo() {
        if (!this.localStream) return;
        this.isVideoMuted = !this.isVideoMuted;
        this.localStream.getVideoTracks().forEach(track => {
            track.enabled = !this.isVideoMuted;
        });

        const camBtn = document.getElementById('btnToggleCam');
        if (camBtn) {
            camBtn.classList.toggle('active-muted', this.isVideoMuted);
            camBtn.innerHTML = this.isVideoMuted ? '<i class="fa-solid fa-video-slash"></i>' : '<i class="fa-solid fa-video"></i>';
        }
    }

    /**
     * End Call session, cleanup streams, and inform server.
     */
    endCall(notifySocket = true) {
        this.stopRingtone();
        if (notifySocket && this.socket && this.activeRoomId) {
            this.socket.emit('end-call', { roomId: this.activeRoomId });
        }

        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }

        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }

        this.remoteStream = null;
        this.setCallState('ended', 'Call Ended');

        setTimeout(() => {
            this.closeCallModal();
        }, 1500);
    }

    // Modal and State helpers
    openCallModal() {
        if (this.modal) this.modal.style.display = 'flex';
    }

    closeCallModal() {
        if (this.modal) this.modal.style.display = 'none';
        this.setCallState('idle', '');
        this.activeRoomId = null;
    }

    setCallState(state, message = '') {
        this.callState = state;
        if (this.statusText) {
            this.statusText.innerText = message || state.toUpperCase();
        }
    }

    // Web Audio Ringtone Synthesizer
    playRingtone(type = 'outgoing') {
        try {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtx) return;
            this.audioCtx = new AudioCtx();

            const playBeep = () => {
                if (!this.audioCtx || this.audioCtx.state === 'closed') return;
                const osc = this.audioCtx.createOscillator();
                const gain = this.audioCtx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(type === 'outgoing' ? 440 : 520, this.audioCtx.currentTime);
                gain.gain.setValueAtTime(0.08, this.audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + 0.6);
                osc.connect(gain);
                gain.connect(this.audioCtx.destination);
                osc.start();
                osc.stop(this.audioCtx.currentTime + 0.6);
            };

            playBeep();
            this.ringtoneInterval = setInterval(playBeep, 2000);
        } catch (e) {
            // Audio context permission or silent fail
        }
    }

    stopRingtone() {
        if (this.ringtoneInterval) {
            clearInterval(this.ringtoneInterval);
            this.ringtoneInterval = null;
        }
        if (this.audioCtx) {
            try { this.audioCtx.close(); } catch (e) {}
            this.audioCtx = null;
        }
    }
}

window.PhidimVideoCall = PhidimVideoCall;
