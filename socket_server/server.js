/**
 * PHIDIM SERVICE REAL-TIME SOCKET.IO & WEBRTC SIGNALING SERVER
 * -----------------------------------------------------------
 * Handles low-latency room-based GPS streaming, throttling,
 * WebRTC signaling (offer, answer, ICE candidates), and instant job updates.
 */

const http = require('http');
const { Server } = require('socket.io');
const dotenv = require('dotenv');
const path = require('path');

// Load environment variables from parent .env if present
dotenv.config({ path: path.join(__dirname, '..', '.env') });

const PORT = process.env.SOCKET_PORT || 5001;

const server = http.createServer((req, res) => {
    // Health check endpoint
    if (req.url === '/health' || req.url === '/') {
        res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
        res.end(JSON.stringify({ status: 'healthy', service: 'phidim-socket-server', timestamp: new Date().toISOString() }));
    } else {
        res.writeHead(404);
        res.end();
    }
});

const io = new Server(server, {
    cors: {
        origin: '*',
        methods: ['GET', 'POST'],
        credentials: true
    },
    pingInterval: 10000,
    pingTimeout: 5000
});

// In-memory registry for throttling and active calls
const activeCalls = new Map(); // roomId -> { callerId, receiverId, requestId, startTime }
const lastLocationUpdates = new Map(); // requestId -> timestamp

io.on('connection', (socket) => {
    console.log(`[Socket Connected] ID: ${socket.id}`);

    // 1. Authenticate / Register User to their personal room
    socket.on('register-user', ({ userId, role, username }) => {
        if (!userId) return;
        socket.userId = String(userId);
        socket.userRole = role;
        socket.username = username;
        
        const userRoom = `user:${userId}`;
        socket.join(userRoom);
        console.log(`[User Registered] ${username || userId} (${role}) joined ${userRoom}`);

        socket.emit('user-registered', { status: 'success', userId, socketId: socket.id });
    });

    // 2. Join Service Request Telemetry Room
    socket.on('join-service-room', ({ requestId, userId, role }) => {
        if (!requestId) return;
        const room = `service-request:${requestId}`;
        socket.join(room);
        console.log(`[Room Joined] User ${userId || socket.id} (${role}) joined ${room}`);

        socket.to(room).emit('participant-joined-room', {
            userId: userId || socket.userId,
            role: role || socket.userRole,
            timestamp: new Date().toISOString()
        });
    });

    // 3. Leave Service Request Telemetry Room
    socket.on('leave-service-room', ({ requestId }) => {
        if (!requestId) return;
        const room = `service-request:${requestId}`;
        socket.leave(room);
        console.log(`[Room Left] ${socket.id} left ${room}`);
    });

    // 4. GPS Location Stream from Technician (with 1.5s rate-limiting / debounce)
    socket.on('technician-location-update', (data) => {
        const { requestId, technicianId, latitude, longitude, accuracy, heading, speed } = data;
        if (!requestId || latitude === undefined || longitude === undefined) return;

        const now = Date.now();
        const lastSent = lastLocationUpdates.get(requestId) || 0;
        
        // Broadcast to customer and participants in the service request room
        const room = `service-request:${requestId}`;
        io.to(room).emit('technician-location-updated', {
            requestId,
            technicianId: technicianId || socket.userId,
            latitude: parseFloat(latitude),
            longitude: parseFloat(longitude),
            accuracy: accuracy || null,
            heading: heading || null,
            speed: speed || null,
            timestamp: new Date().toISOString()
        });

        lastLocationUpdates.set(requestId, now);
    });

    // 5. Service Status Change Broadcast
    socket.on('service-status-update', ({ requestId, status, statusDisplay, message }) => {
        if (!requestId) return;
        const room = `service-request:${requestId}`;
        io.to(room).emit('service-status-changed', {
            requestId,
            status,
            statusDisplay,
            message,
            timestamp: new Date().toISOString()
        });
    });

    // ----------------------------------------------------
    // WEBRTC VIDEO CALL SIGNALING
    // ----------------------------------------------------

    // A. Initiate Outgoing Call
    socket.on('call-user', ({ targetUserId, requestId, roomId, callerName, callerAvatar, serviceTitle }) => {
        if (!targetUserId || !roomId) return;
        console.log(`[Call Initiated] From ${socket.userId || socket.id} to Target User ${targetUserId} in Room ${roomId}`);

        activeCalls.set(roomId, {
            callerSocketId: socket.id,
            callerUserId: socket.userId,
            targetUserId: String(targetUserId),
            requestId,
            roomId,
            status: 'calling',
            startedAt: Date.now()
        });

        socket.join(`call-room:${roomId}`);

        // Notify target user via their personal room
        io.to(`user:${targetUserId}`).emit('incoming-call', {
            callerId: socket.userId,
            callerSocketId: socket.id,
            callerName: callerName || socket.username || 'Client',
            callerAvatar: callerAvatar || '',
            requestId,
            roomId,
            serviceTitle: serviceTitle || 'Service Video Consultation'
        });
    });

    // B. Call Accepted by Receiver
    socket.on('accept-call', ({ roomId, callerSocketId }) => {
        if (!roomId) return;
        console.log(`[Call Accepted] Room ${roomId} by ${socket.userId || socket.id}`);

        socket.join(`call-room:${roomId}`);
        const callData = activeCalls.get(roomId);
        if (callData) {
            callData.status = 'connected';
            callData.receiverSocketId = socket.id;
        }

        // Notify caller that receiver accepted
        io.to(`call-room:${roomId}`).emit('call-accepted', {
            roomId,
            receiverSocketId: socket.id,
            receiverUserId: socket.userId
        });
    });

    // C. Call Rejected
    socket.on('reject-call', ({ roomId, callerSocketId, reason }) => {
        console.log(`[Call Rejected] Room ${roomId}`);
        if (roomId && activeCalls.has(roomId)) {
            activeCalls.delete(roomId);
        }
        if (callerSocketId) {
            io.to(callerSocketId).emit('call-rejected', { roomId, reason: reason || 'Declined by recipient' });
        }
    });

    // D. End / Hangup Call
    socket.on('end-call', ({ roomId }) => {
        console.log(`[Call Ended] Room ${roomId}`);
        if (roomId) {
            io.to(`call-room:${roomId}`).emit('call-ended', { roomId, reason: 'User hung up' });
            activeCalls.delete(roomId);
        }
    });

    // E. WebRTC SDP Offer
    socket.on('webrtc-offer', ({ roomId, offer }) => {
        socket.to(`call-room:${roomId}`).emit('webrtc-offer', { offer, senderSocketId: socket.id });
    });

    // F. WebRTC SDP Answer
    socket.on('webrtc-answer', ({ roomId, answer }) => {
        socket.to(`call-room:${roomId}`).emit('webrtc-answer', { answer, senderSocketId: socket.id });
    });

    // G. WebRTC ICE Candidate
    socket.on('webrtc-ice-candidate', ({ roomId, candidate }) => {
        socket.to(`call-room:${roomId}`).emit('webrtc-ice-candidate', { candidate, senderSocketId: socket.id });
    });

    // H. In-Call Chat Message
    socket.on('send-room-chat', ({ roomId, requestId, message, senderName }) => {
        const targetRoom = roomId ? `call-room:${roomId}` : `service-request:${requestId}`;
        io.to(targetRoom).emit('new-room-chat', {
            message,
            senderName: senderName || socket.username || 'User',
            senderId: socket.userId,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });
    });

    // Handle Disconnection
    socket.on('disconnect', () => {
        console.log(`[Socket Disconnected] ID: ${socket.id} (User: ${socket.userId || 'anon'})`);
        
        // Clean up any pending active calls for this socket
        for (const [roomId, call] of activeCalls.entries()) {
            if (call.callerSocketId === socket.id || call.receiverSocketId === socket.id) {
                io.to(`call-room:${roomId}`).emit('call-ended', { roomId, reason: 'Participant disconnected' });
                activeCalls.delete(roomId);
            }
        }
    });
});

server.listen(PORT, () => {
    console.log(`\n======================================================`);
    console.log(`🚀 Phidim Real-time Socket & WebRTC Server Running`);
    console.log(`📡 Listening on: http://localhost:${PORT}`);
    console.log(`======================================================\n`);
});
