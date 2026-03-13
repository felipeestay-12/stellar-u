import socketio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os
import socket

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('192.168.0.2', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


script_dir = os.path.dirname(os.path.abspath(__file__))

static_file_path = os.path.join(script_dir, "static")

# Crear servidor Socket.IO
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
sio_app = socketio.ASGIApp(sio, app)

# Archivos estáticos y templates
app.mount("/static", StaticFiles(directory=static_file_path), name="static")
templates = Jinja2Templates(directory=os.path.join(script_dir, "templates"))

# --- RUTAS DE ACCESO ---

@app.get("/", response_class=HTMLResponse)
async def controlador(request: Request):
    """Esta es la interfaz para TU NOTEBOOK (Control)"""
    return templates.TemplateResponse("control.html", {"request": request})

@app.get("/robot", response_class=HTMLResponse)
async def robot_face(request: Request):
    """Esta es la página que abrirá el NUC automáticamente"""
    return templates.TemplateResponse("robot.html", {"request": request})

# --- LÓGICA DE CONEXIÓN (SIGNALING) ---

@sio.event
async def connect(sid, environ):
    print(f"Conectado: {sid}")

@sio.event
async def join_room(sid, data):
    room = data['room']
    await sio.enter_room(sid, room)
    print(f"Usuario {sid} se unió a la sala: {room}")
    # Avisar a los otros en la sala que alguien llegó listo para hablar
    await sio.emit('user_joined', {'sid': sid}, room=room, skip_sid=sid)

# Estos eventos pasan los mensajes de WebRTC (Offer, Answer, ICE Candidates)
# de un navegador a otro a través del servidor Python
@sio.event
async def signal(sid, data):
    # Reenviar la señal al destinatario específico
    target_sid = data['target']
    await sio.emit('signal', {
        'sender': sid,
        'type': data['type'],
        'sdp': data.get('sdp'),
        'candidate': data.get('candidate')
    }, room=target_sid)

@sio.event
async def toggle_ai(sid, data):
    print(f" Toggle AI solicitado por {sid}: {data}")
    # Reenviar a todos (incluyendo el script de Python que escucha)
    await sio.emit('toggle_ai', data)


@sio.event
async def disconnect(sid):
    print(f"Desconectado: {sid}")

@sio.event
async def connect(sid, environ):
    print(f"🔌 Cliente conectado: {sid}")

# @sio.event
# def toggle_ai(data):
#     global AI_ENABLED
#     AI_ENABLED = bool(data.get("enabled", False))
#     print(f"🤖 Modo IA {'ACTIVADO' if AI_ENABLED else 'DESACTIVADO'}")

# @sio.event
# async def audio_stream(sid, data):
#     # This listens for the microphone data (Blob) from main.js
#     # 'data' is the binary file (bytes)
#     print(f"🎤 Audio received: {len(data)} bytes")
    
#     # Save it to a file to check if it works
#     with open("incoming_audio.webm", "wb") as f:
#         f.write(data)
    
#     print("💾 Audio saved as 'incoming_audio.webm'")

@sio.event
async def command(sid, data):
    # This function listens for the 'command' event sent by main.js
    action = data.get('action')
    print(action)
    if action == 'move':
        direction = data.get('direction')
        print(f"🚗 COMMAND RECEIVED: Move {direction}")
        
        # TODO: Connect your motor driver here
        # Example:
        # if direction == 'up': motors.forward()
        # elif direction == 'down': motors.backward()
        
    elif action == 'stop':
        print("🛑 COMMAND RECEIVED: Stop")
        # TODO: Connect motor stop here
        # motors.stop()

    elif action == 'mute':
        print("🛑 COMMAND RECEIVED: Mute")

if __name__ == '__main__':
    # Ejecutar en la red local
    ip_address = get_local_ip()
    print(f"🚀 Servidor listo. Accede desde otros PC/Móviles en: http://{ip_address}:8000")
    uvicorn.run(sio_app, host='0.0.0.0', port=8000)