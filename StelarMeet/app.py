from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
# El cors_allowed_origins="*" permite que tu PC de escritorio se conecte sin bloqueos
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html') # Tu HTML con el CSS que arreglamos

# --- RECEPCIÓN DE COMANDOS DE MOVIMIENTO ---
@socketio.on('comando_motor')
def handle_motor(data):
    print(f"Robot recibiendo señal: {data['accion']}") 
    # Aquí es donde Python hablaría con los motores reales (Arduino/GPIO)
    emit('status_robot', {'msg': f"Ejecutando {data['accion']}"}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)