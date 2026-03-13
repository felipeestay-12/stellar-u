// static/webrtc_logic.js

var socket = window.socket || io();
window.socket = socket;
let localStream;
let peerConnection;

// Configuración de servidores STUN (Google)
const config = {
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
};

async function iniciarWebRTC(room, soyElRobot) {
    console.log(`Iniciando WebRTC. Soy Robot: ${soyElRobot}`);
    
    // 1. CONFIGURACIÓN DE MEDIA (CÁMARA/MIC)
    try {

        const constraints = soyElRobot 
            ? { video: false, audio: true }  // Robot: Envío solo Audio
            : { video: true, audio: true };  // Control: Envio Video y Audio
            
        localStream = await navigator.mediaDevices.getUserMedia(constraints);
        
        // Mostrar mi propia cámara (Solo útil para ver si mi cámara funciona antes de enviar)
        if (!soyElRobot) {
            const localVid = document.getElementById('localVideo');
            if (localVid) {
                localVid.srcObject = localStream;
                localVid.muted = true; // Mute local para no escuchar mi propio eco
            }
        }
    } catch (e) {
        console.error("Error obteniendo media:", e);
        // Si falla, seguimos la ejecución para intentar recibir video aunque no tengamos cámara.
    }

    // 2. UNIRSE A LA SALA
    socket.emit('join_room', { room: room });

    // 3. LÓGICA DE LLAMADA (CORREGIDA)
    socket.on('user_joined', async (data) => {
        console.log("👋 Usuario nuevo detectado:", data.sid);
        
        // Logica Actual: El CONTROLADOR llama al Robot.
        // Cuando el controlador entra y ve que hay alguien (el robot), inicia la oferta.
        if (!soyElRobot) {
            console.log("Soy el Controlador. Iniciando llamada al Robot...");
            iniciarLlamada(data.sid);
        }
    });

    // 4. MANEJO DE SEÑALES
    socket.on('signal', async (data) => {
        // Si recibimos señal (una llamada entrante) y no tenemos conexión, la preparamos.
        if (!peerConnection) crearPeerConnection(data.sender, soyElRobot);

        if (data.type === 'offer') {
            console.log("📩 Recibida oferta de conexión...");
            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp));
            
            const answer = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(answer);
            
            socket.emit('signal', { target: data.sender, type: 'answer', sdp: answer });
        } 
        else if (data.type === 'answer') {
            console.log("La otra parte contestó la llamada.");
            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp));
        } 
        else if (data.type === 'candidate') {
            if (data.candidate) {
                try {
                    await peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
                } catch (e) {
                    console.error("Error agregando candidato ICE", e);
                }
            }
        }
    });
}

// Función para iniciar la oferta de llamada
async function iniciarLlamada(targetSid) {
    crearPeerConnection(targetSid, false); // false = soy control
    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);
    
    socket.emit('signal', { target: targetSid, type: 'offer', sdp: offer });
}

function crearPeerConnection(targetSid, soyElRobot) {
    console.log("🛠️ Creando PeerConnection...");
    peerConnection = new RTCPeerConnection(config);

    // A. AGREGAR MIS TRACKS (Lo que yo envío por el cable)
    if (localStream) {
        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });
    }

    // B. MANEJAR TRACKS REMOTOS (Lo que recibo del otro lado)
    peerConnection.ontrack = (event) => {
        console.log("¡Recibiendo stream remoto!");
        const remoteVid = document.getElementById('remoteVideo'); 
        const remoteAud = document.getElementById('remoteAudio'); // Asegúrate de tener <audio id="remoteAudio">

        // Si soy Robot: Aquí llega el VIDEO del Controlador.
        // Si soy Controlador: Aquí llega solo el AUDIO del Robot (si tiene mic).
        if (remoteVid && event.streams[0]) {
            remoteVid.srcObject = event.streams[0];
        }
        
        // Conectar el audio (esto aplica para ambos lados)
        if (remoteAud && event.streams[0]) {
            remoteAud.srcObject = event.streams[0];
        }
    };

    // C. MANEJAR CANDIDATOS ICE (Rutas de red)
    peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
            socket.emit('signal', { 
                target: targetSid, 
                type: 'candidate', 
                candidate: event.candidate 
            });
        }
    };
    
    // Monitor de estado (Opcional, ayuda a depurar)
    peerConnection.onconnectionstatechange = () => {
        console.log("Estado de conexión:", peerConnection.connectionState);
    };
}