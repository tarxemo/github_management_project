
        // Improved call state management
        const callStates = {
            IDLE: 'idle',
            CALLING: 'calling',
            RINGING: 'ringing',
            ACTIVE: 'active',
            ENDED: 'ended'
        };
        
        let currentCallState = callStates.IDLE;
        let callStartTime;
        let callTimer;
        let peerConnection;
        let localStream;
        let remoteStream;
        let audioContext, analyser, source;
        
        const userId = "{{ request.user.id }}";
        const username = "{{ request.user.username }}";
        const socket = new WebSocket(
            ("https:" === window.location.protocol ? "wss://" : "ws://") +
            window.location.host + "/ws/call/"
        );
        
        const configuration = {
            iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
        };
        
        // DOM Elements
        const incomingCallModal = document.getElementById("incoming-call");
        const incomingCaller = document.getElementById("incoming-caller");
        const muteButton = document.getElementById("mute-button");
        const speakerButton = document.getElementById("speaker-button");
        const endCallButton = document.getElementById("end-call");
        const acceptCallButton = document.getElementById("accept-call");
        const callDuration = document.getElementById("call-duration");
        const callStatus = document.getElementById("call-status");
        const callStateTitle = document.getElementById("call-state-title");
        const callHeader = document.getElementById("call-header");
        const waveformContainer = document.getElementById("waveform-container");
        const callerName = document.getElementById("caller-name");
        const callerSpecialty = document.getElementById("caller-specialty");
        const callerAvatar = document.getElementById("caller-avatar");
        const remoteAudio = document.getElementById("remoteAudio");
        
        // Update call UI based on state
        function updateCallUI(state) {
            switch (state) {
                case callStates.CALLING:
                    callStateTitle.textContent = "Calling...";
                    callStatus.textContent = "Waiting for answer";
                    callHeader.className = "bg-gray-600 text-white p-6 text-center";
                    acceptCallButton.classList.add("hidden");
                    endCallButton.classList.remove("hidden");
                    waveformContainer.classList.add("hidden");
                    break;
                    
                case callStates.RINGING:
                    callStateTitle.textContent = "Incoming Call";
                    callStatus.textContent = "Ringing...";
                    callHeader.className = "bg-green-600 text-white p-6 text-center";
                    acceptCallButton.classList.remove("hidden");
                    endCallButton.classList.remove("hidden");
                    waveformContainer.classList.add("hidden");
                    break;
                    
                case callStates.ACTIVE:
                    callStateTitle.textContent = "Call Connected";
                    callStatus.textContent = "In progress";
                    callHeader.className = "bg-green-600 text-white p-6 text-center";
                    acceptCallButton.classList.add("hidden");
                    endCallButton.classList.remove("hidden");
                    waveformContainer.classList.remove("hidden");
                    startCallTimer();
                    break;
                    
                case callStates.ENDED:
                    callStateTitle.textContent = "Call Ended";
                    callStatus.textContent = "Connection terminated";
                    callHeader.className = "bg-gray-500 text-white p-6 text-center";
                    acceptCallButton.classList.add("hidden");
                    endCallButton.classList.add("hidden");
                    waveformContainer.classList.add("hidden");
                    
                    // Show call duration briefly before closing
                    setTimeout(() => {
                        hideIncomingCall();
                    }, 2000);
                    break;
                    
                default:
                    hideIncomingCall();
            }
        }
        
        // Show incoming call with proper state
        function showIncomingCall(callerName, callerId, isIncoming = true) {
            currentCallState = isIncoming ? callStates.RINGING : callStates.CALLING;
            incomingCaller.textContent = isIncoming ? `From ${callerName}` : `To ${callerName}`;
            window.callerId = callerId;
            incomingCallModal.classList.remove("hidden");
            updateCallUI(currentCallState);
        }
        
        function hideIncomingCall() {
            incomingCallModal.classList.add("hidden");
            currentCallState = callStates.IDLE;
            resetWebRTC();
        }
        
        // Proper call termination
        function endCall() {
            if (currentCallState === callStates.ENDED) return;
            
            currentCallState = callStates.ENDED;
            updateCallUI(currentCallState);
            
            // Send end call signal if connection exists
            if (socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    action: "end_call",
                    target_user: window.callerId || window.targetUserId
                }));
            }
            
            stopCallTimer();
            resetWebRTC();
        }
        
        function startCallTimer() {
            callStartTime = new Date();
            callTimer = setInterval(() => {
                const now = new Date();
                const elapsed = Math.floor((now - callStartTime) / 1000);
                const minutes = Math.floor(elapsed / 60).toString().padStart(2, "0");
                const seconds = (elapsed % 60).toString().padStart(2, "0");
                callDuration.textContent = `${minutes}:${seconds}`;
            }, 1000);
        }
        
        function stopCallTimer() {
            if (callTimer) {
                clearInterval(callTimer);
                callTimer = null;
            }
        }
        
        // Improved call initiation
        async function callUser(targetUserId, targetUserName) {
            try {
                // Initialize local stream
                localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                console.log("Microphone access granted");
                
                // Set up peer connection
                peerConnection = new RTCPeerConnection(configuration);
                
                // Set call state and UI
                window.initiator = username;
                showIncomingCall(targetUserName, targetUserId, false);
                
                // Add local tracks
                localStream.getTracks().forEach(track => {
                    console.log("Adding local track:", track);
                    peerConnection.addTrack(track, localStream);
                });
                
                // ICE candidate handling
                peerConnection.onicecandidate = event => {
                    if (event.candidate) {
                        console.log("New ICE candidate:", event.candidate);
                        socket.send(JSON.stringify({
                            action: "ice_candidate",
                            candidate: event.candidate,
                            target_user: targetUserId
                        }));
                    }
                };
                
                // Remote stream handling
                peerConnection.ontrack = event => {
                    console.log("Remote stream received:", event.streams[0]);
                    remoteStream = event.streams[0];
                    remoteAudio.srcObject = remoteStream;
                    
                    // Play the remote audio
                    remoteAudio.play().catch(error => {
                        console.error("Error playing remote audio:", error);
                    });
                    
                    // Initialize audio visualization
                    initAudioVisualization(remoteAudio);
                    
                    // Update call state to active
                    currentCallState = callStates.ACTIVE;
                    updateCallUI(currentCallState);
                };
                
                // Connection state changes
                peerConnection.onconnectionstatechange = () => {
                    console.log("Connection state:", peerConnection.connectionState);
                    if (peerConnection.connectionState === "disconnected" || 
                        peerConnection.connectionState === "failed") {
                        endCall();
                    }
                };
                
                // Send call initiation
                socket.send(JSON.stringify({
                    action: "call",
                    target_user: targetUserId
                }));
                
            } catch (error) {
                console.error("Error initiating call:", error);
                alert("Could not start the call. Please check your microphone permissions.");
                endCall();
            }
        }
        
        // Improved call acceptance
        async function acceptCall() {
            try {
                // Send acceptance to the caller
                socket.send(JSON.stringify({
                    action: "accept",
                    caller_id: window.callerId
                }));
                
                // Initialize WebRTC as callee
                await startWebRTC(false);
                
                // Update call state
                currentCallState = callStates.ACTIVE;
                updateCallUI(currentCallState);
                
            } catch (error) {
                console.error("Error accepting call:", error);
                endCall();
            }
        }
        
        // Improved WebRTC setup
        async function startWebRTC(isCaller) {
            try {
                // Create or reuse peer connection
                if (!peerConnection) {
                    peerConnection = new RTCPeerConnection(configuration);
                    
                    // Set up event handlers
                    peerConnection.onicecandidate = event => {
                        if (event.candidate) {
                            console.log("New ICE candidate:", event.candidate);
                            socket.send(JSON.stringify({
                                action: "ice_candidate",
                                candidate: event.candidate,
                                target_user: window.callerId
                            }));
                        }
                    };
                    
                    peerConnection.ontrack = event => {
                        console.log("Remote stream received:", event.streams[0]);
                        remoteStream = event.streams[0];
                        remoteAudio.srcObject = remoteStream;
                        remoteAudio.play().catch(error => {
                            console.error("Error playing remote audio:", error);
                        });
                        initAudioVisualization(remoteAudio);
                    };
                    
                    peerConnection.onconnectionstatechange = () => {
                        console.log("Connection state:", peerConnection.connectionState);
                    };
                }
                
                // Get local media if not already available
                if (!localStream) {
                    localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    console.log("Local stream created:", localStream);
                }
                
                // Add local tracks if not already added
                const senders = peerConnection.getSenders();
                if (senders.length === 0) {
                    localStream.getTracks().forEach(track => {
                        console.log("Adding local track:", track);
                        peerConnection.addTrack(track, localStream);
                    });
                }
                
                // Create and send offer if caller
                if (isCaller) {
                    const offer = await peerConnection.createOffer();
                    await peerConnection.setLocalDescription(offer);
                    console.log("Sending offer:", offer);
                    
                    socket.send(JSON.stringify({
                        action: "offer",
                        offer: offer,
                        target_user: window.callerId
                    }));
                }
                
            } catch (error) {
                console.error("Error in WebRTC setup:", error);
                endCall();
            }
        }
        
        // Handle incoming offers
        async function handleOffer(offer) {
            console.log("Received offer:", offer);
            
            // Initialize WebRTC if not already done
            if (!peerConnection) {
                await startWebRTC(false);
            }
            
            // Set remote description
            await peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
            
            // Process any queued ICE candidates
            while (queuedIceCandidates.length > 0) {
                const candidate = queuedIceCandidates.shift();
                console.log("Processing queued ICE candidate:", candidate);
                await peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
            }
            
            // Create and send answer
            const answer = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(answer);
            console.log("Sending answer:", answer);
            
            socket.send(JSON.stringify({
                action: "answer",
                answer: answer,
                target_user: window.callerId
            }));
        }
        
        // Handle incoming answers
        async function handleAnswer(answer) {
            console.log("Received answer:", answer);
            await peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
        }
        
        // Handle ICE candidates
        let queuedIceCandidates = [];
        async function handleNewICECandidate(candidate) {
            try {
                if (!peerConnection) {
                    console.warn("peerConnection is not initialized yet. Queuing ICE candidate.");
                    queuedIceCandidates.push(candidate);
                    return;
                }
                
                if (!peerConnection.remoteDescription) {
                    console.log("Remote description not set. Queuing ICE candidate:", candidate);
                    queuedIceCandidates.push(candidate);
                    return;
                }
                
                console.log("Adding ICE candidate:", candidate);
                await peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
            } catch (error) {
                console.error("Error adding ICE candidate:", error);
            }
        }
        
        // Clean up WebRTC resources
        function resetWebRTC() {
            if (peerConnection) {
                peerConnection.close();
                peerConnection = null;
            }
            
            if (localStream) {
                localStream.getTracks().forEach(track => track.stop());
                localStream = null;
            }
            
            if (remoteStream) {
                remoteStream.getTracks().forEach(track => track.stop());
                remoteStream = null;
            }
            
            if (audioContext) {
                audioContext.close();
                audioContext = null;
            }
            
            queuedIceCandidates = [];
            remoteAudio.srcObject = null;
        }
        
        // Audio visualization
        function initAudioVisualization(audioElement) {
            try {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                analyser = audioContext.createAnalyser();
                source = audioContext.createMediaStreamSource(audioElement.srcObject);
                
                source.connect(analyser);
                analyser.connect(audioContext.destination);
                analyser.fftSize = 256;
                
                const bufferLength = analyser.frequencyBinCount;
                const dataArray = new Uint8Array(bufferLength);
                
                function draw() {
                    if (currentCallState !== callStates.ACTIVE) return;
                    
                    requestAnimationFrame(draw);
                    analyser.getByteFrequencyData(dataArray);
                    
                    const canvas = document.getElementById("audio-visualization");
                    const canvasCtx = canvas.getContext("2d");
                    
                    canvasCtx.fillStyle = "rgb(200, 200, 200)";
                    canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
                    
                    const barWidth = (canvas.width / bufferLength) * 2.5;
                    let x = 0;
                    
                    for (let i = 0; i < bufferLength; i++) {
                        const barHeight = dataArray[i] / 2;
                        canvasCtx.fillStyle = `rgb(${barHeight + 100}, 50, 50)`;
                        canvasCtx.fillRect(x, canvas.height - barHeight / 2, barWidth, barHeight);
                        x += barWidth + 1;
                    }
                }
                
                draw();
            } catch (error) {
                console.error("Error initializing audio visualization:", error);
            }
        }
        
        // Event listeners
        speakerButton.addEventListener("click", () => {
            if (remoteAudio.volume === 1) {
                remoteAudio.volume = 0.5;
                speakerButton.innerHTML = '<i class="fas fa-volume-down"></i>';
            } else {
                remoteAudio.volume = 1;
                speakerButton.innerHTML = '<i class="fas fa-volume-up"></i>';
            }
        });
        
        endCallButton.addEventListener("click", endCall);
        acceptCallButton.addEventListener("click", acceptCall);
        
        muteButton.addEventListener("click", () => {
            if (localStream) {
                const audioTracks = localStream.getAudioTracks();
                audioTracks.forEach(track => {
                    track.enabled = !track.enabled;
                    muteButton.innerHTML = track.enabled 
                        ? '<i class="fas fa-microphone"></i>'
                        : '<i class="fas fa-microphone-slash"></i>';
                });
            }
        });
        
        // WebSocket message handling
        socket.onmessage = function(event) {
            const data = JSON.parse(event.data);
            console.log("WebSocket message received:", data);
            
            switch (data.action) {
                case "incoming_call":
                    showIncomingCall(data.caller_name, data.caller_id);
                    window.callerId = data.caller_id;
                    window.callerUsername = data.caller_name;
                    break;
                    
                case "call_accepted":
                    startWebRTC(true);
                    break;
                    
                case "call_rejected":
                    currentCallState = callStates.ENDED;
                    updateCallUI(currentCallState);
                    setTimeout(hideIncomingCall, 1500);
                    break;
                    
                case "offer":
                    handleOffer(data.offer);
                    break;
                    
                case "answer":
                    handleAnswer(data.answer);
                    break;
                    
                case "ice_candidate":
                    handleNewICECandidate(data.candidate);
                    break;
                    
                case "end_call":
                    currentCallState = callStates.ENDED;
                    updateCallUI(currentCallState);
                    setTimeout(hideIncomingCall, 1500);
                    break;
                    
                default:
                    console.warn("Unknown action:", data.action);
            }
        };
        
        // Handle window close or page navigation
        window.addEventListener("beforeunload", () => {
            if (currentCallState === callStates.ACTIVE || 
                currentCallState === callStates.CALLING ||
                currentCallState === callStates.RINGING) {
                endCall();
            }
        });
