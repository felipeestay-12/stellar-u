from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)

# CONFIGURACIÓN CRÍTICA PARA VIDEO:
# 1. max_http_buffer_size: Subimos a 20MB para que quepan los frames de video sin errores.
# 2. ping_timeout/interval: Evita que el servidor desconecte al robot si la red se satura.
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    max_http_buffer_size=20000000,
    ping_timeout=600,      # Aumentamos a 60 segundos
    ping_interval=25,     # Comprobamos conexión cada 25 segundos
    always_connect=True
)

# --- CANALES DE VIDEO (Robot -> PC) ---
@socketio.on('robot_video_front')
def handle_front(data):
    emit('ver_front', data, broadcast=True, include_self=False)

@socketio.on('robot_video_rear')
def handle_rear(data):
    emit('ver_rear', data, broadcast=True, include_self=False)

@app.route('/')
def index():
    return render_template('control.html')

@app.route('/robot')
def robot():
    return render_template('robot.html')

@app.route('/video_control')
def video_control():
    return render_template('video_control.html')

# --- CANAL DE VIDEO (PC Externo -> Robot) ---
@socketio.on('video_frame')
def handle_video_frame(data):
    # Recibe el frame de video_control.html y lo reenvía a robot.html
    # Usamos un evento con nombre distinto para evitar confusiones de protocolo
    emit('display_frame', data, broadcast=True, include_self=False)

# --- CANALES DE AUDIO ---

@socketio.on('audio_chunk')
def handle_audio(data):
    # PC -> Robot (Tu voz hacia la laptop)
    emit('audio_stream', data, broadcast=True, include_self=False)

@socketio.on('robot_audio_to_server')
def handle_robot_audio(data):
    # Robot -> PC (El sonido de la laptop hacia tu PC)
    emit('audio_from_robot', data, broadcast=True, include_self=False)

# --- CANAL DE COMANDOS (BOTONES) ---

@socketio.on('command')
def handle_commands(data):
    # Reenviamos el comando para que ambos dispositivos estén sincronizados
    emit('command', data, broadcast=True, include_self=False)
    
    action = data.get('action')
    enabled = data.get('enabled', False)
    direction = data.get('direction', 'N/A')
    
    mensajes = {
        'ia': "🧠 IA",
        'saludo': "👋 SALUDO",
        'mic': "🎙️ MIC",
        'video': "📷 VIDEO",
        'ubicacion': "📍 RUTA",
        'onoff': "⚡ POWER",
        'start': f"🕹️ MOVIMIENTO: {direction}",
        'stop': "🛑 STOP"
    }
    
    if action in mensajes:
        if action == 'saludo' or 'start' in action:
            print(mensajes[action])
        else:
            print(f"{mensajes[action]}: {'ON' if enabled else 'OFF'}")

if __name__ == '__main__':
    # Usamos log_output=True para monitorear las conexiones en tiempo real
    # debug=False es más estable para transmisión de video
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, log_output=True)