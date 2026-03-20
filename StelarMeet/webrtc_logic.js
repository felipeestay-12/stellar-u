// static/webrtc_logic.js

var socket = window.socket || io();
window.socket = socket;
let localStream = new MediaStream(); // Inicializamos como un stream vacío
let peerConnection;

const config = {
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
};

async function iniciarWebRTC(room, soyElRobot) {
    console.log(`Iniciando WebRTC. Soy Robot: ${soyElRobot}`);
    
    try {
        // --- CAMBIO CRÍTICO: CAPTURA DE MÚLTIPLES CÁMARAS ---
        if (!soyElRobot) {
            // El controlador busca todas las cámaras disponibles
            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter(device => device.kind === 'videoinput');

            for (const device of videoDevices) {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { deviceId: { exact: device.deviceId } },
                    audio: true
                });
                // Añadimos cada track de cada cámara al localStream unificado
                stream.getTracks().forEach(track => localStream.addTrack(track));
            }

            const localVid = document.getElementById('localVideo');
            if (localVid) {
                localVid.srcObject = localStream;
                localVid.muted = true;
            }
        } else {
            // El Robot solo envía audio (puedes cambiar a video:true si el robot también tiene cámara)
            const audioStream = await navigator.mediaDevices.getUserMedia({ video: false, audio: true });
            audioStream.getTracks().forEach(track => localStream.addTrack(track));
        }
    } catch (e) {
        console.error("Error obteniendo media:", e);
    }

    socket.emit('join_room', { room: room });

    socket.on('user_joined', async (data) => {
        if (!soyElRobot) {
            iniciarLlamada(data.sid);
        }
    });

    socket.on('signal', async (data) => {
        if (!peerConnection) crearPeerConnection(data.sender, soyElRobot);

        if (data.type === 'offer') {
            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp));
            const answer = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(answer);
            socket.emit('signal', { target: data.sender, type: 'answer', sdp: answer });
        } 
        else if (data.type === 'answer') {
            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp));
        } 
        else if (data.type === 'candidate' && data.candidate) {
            await peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
        }
    });
}

async function iniciarLlamada(targetSid) {
    crearPeerConnection(targetSid, false);
    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);
    socket.emit('signal', { target: targetSid, type: 'offer', sdp: offer });
}

function crearPeerConnection(targetSid, soyElRobot) {
    peerConnection = new RTCPeerConnection(config);

    if (localStream) {
        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });
    }

    peerConnection.ontrack = (event) => {
        // --- CAMBIO PARA VISUALIZAR SEGUNDA CÁMARA ---
        // Buscamos si hay un segundo elemento de video en el HTML
        const remoteVid1 = document.getElementById('remoteVideo');
        const remoteVid2 = document.getElementById('remoteVideo2'); 

        // Asignamos el stream al primer video, y si hay más tracks, al segundo
        if (remoteVid1 && !remoteVid1.srcObject) {
            remoteVid1.srcObject = event.streams[0];
        } else if (remoteVid2 && !remoteVid2.srcObject) {
            remoteVid2.srcObject = event.streams[0];
        }
    };

    peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
            socket.emit('signal', { target: targetSid, type: 'candidate', candidate: event.candidate });
        }
    };
}