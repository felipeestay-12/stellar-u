from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import random
import threading
import time
import os
import sys
import requests

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'stelar_secret_88'

# MEJORA 1: Ajustamos los tiempos de ping para evitar que la API de voz se desconecte
socketio = SocketIO(app, 
    cors_allowed_origins="*", 
    async_mode='threading', 
    ping_timeout=10, 
    ping_interval=5
)

# --- ESTADOS GLOBALES DEL ROBOT ---
robot_state = {
    'moving': False,
    'direction': None,
    'speed_val': 0.0,
    'battery': 100.0,
    'camera_active': 1, 
    'ai_active': False
}

@app.route('/')
def index():
    return render_template('control.html')

# --- LÓGICA DE IA (OLLAMA / LLM) ---
def talk_to_ollama(prompt):
    try:
        url = "http://localhost:11434/api/generate"
        data = {
            "model": "llama3", 
            "prompt": prompt,
            "stream": False
        }
        # Solo imprimimos en el emulador, no spameamos conexiones
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()['response']
        return "Error en Ollama API"
    except Exception as e:
        return f"Ollama no detectado"

# --- SIMULADOR DE FÍSICA Y TELEMETRÍA ---
def robot_physics_loop():
    while True:
        if robot_state['battery'] > 0:
            drain = 0.02 
            if robot_state['moving']: drain += 0.05
            if robot_state['ai_active']: drain += 0.1
            robot_state['battery'] = max(0, robot_state['battery'] - drain)

        target_speed = 1.5 if robot_state['moving'] else 0.0
        if robot_state['speed_val'] < target_speed:
            robot_state['speed_val'] += 0.1
        elif robot_state['speed_val'] > target_speed:
            robot_state['speed_val'] -= 0.1
        
        robot_state['speed_val'] = max(0, round(robot_state['speed_val'], 2))
        wifi_stats = random.choice(["Excelente", "Estable", "85%", "-42dBm"])
        
        # Enviamos la telemetría solo a los interesados
        socketio.emit('status_update', {
            'battery': round(robot_state['battery'], 1),
            'wifi': wifi_stats,
            'speed': robot_state['speed_val'],
            'camera': f"CAM 0{robot_state['camera_active']} - ACTIVA"
        })
        
        time.sleep(1.0) # Aumentamos a 1s para no saturar el canal

# --- MANEJO DE COMANDOS ---
@socketio.on('command')
def handle_command(data):
    action = data.get('action')
    enabled = data.get('enabled')
    direction = data.get('direction')

    if action == 'ia':
        robot_state['ai_active'] = enabled
        # MEJORA 2: Emitimos a la API de Voz con broadcast para que todos se enteren
        socketio.emit('toggle_ai', {'enabled': enabled})
        print(f"📡 EVENTO ENVIADO: toggle_ai -> {enabled}")
        
        if enabled:
            def saludo():
                # Evitamos que el saludo bloquee el hilo principal
                print("🧠 [Ollama] Generando saludo inicial...")
                res = talk_to_ollama("Preséntate brevemente (máximo 15 palabras) como Stelarbot, un asistente robótico.")
                socketio.emit('server_log', res)
            threading.Thread(target=saludo).start()

    elif action == 'start':
        robot_state['moving'] = True
        robot_state['direction'] = direction
    elif action == 'stop':
        robot_state['moving'] = False
    elif action == 'video':
        robot_state['camera_active'] = 2 if enabled else 1

# --- RECEPTOR DE LOGS (Para que la API de voz escriba en el HUD) ---
@socketio.on('server_log')
def handle_server_log(message):
    # Cuando la API de voz manda texto, lo reenviamos al HUD
    socketio.emit('server_log', message)

@socketio.on('connect')
def handle_connect():
    # Solo imprimimos una vez para no llenar la consola si hay reconexiones
    print(f"🔌 Conexión establecida")

if __name__ == '__main__':
    t_physics = threading.Thread(target=robot_physics_loop, daemon=True)
    t_physics.start()
    
    print("\n" + "="*50)
    print("🤖 EMULADOR STELARBOT (VERSIÓN OPTIMIZADA)")
    print("🔗 HUD: http://localhost:5000")
    print("="*50 + "\n")
    
    try:
        # MEJORA 3: Forzamos el uso de eventlet o threading puro para evitar conflictos
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        sys.exit(0)