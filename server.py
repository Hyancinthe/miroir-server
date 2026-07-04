from flask import Flask, request, jsonify
from datetime import datetime
import os

app = Flask(__name__)

# Stockage en mémoire (Render free = pas de persistence disque)
locations = {}

@app.route('/')
def home():
    return jsonify({
        "service": "Miroir Tracker",
        "agents": len(locations),
        "status": "online"
    })

@app.route('/report', methods=['POST'])
def report():
    """Un agent envoie sa position"""
    try:
        data = request.get_json()
        serial = data.get('serial', 'unknown')
        locations[serial] = {
            'serial': serial,
            'lat': data['lat'],
            'lng': data['lng'],
            'precision': data.get('precision', 0),
            'source': data.get('source', 'agent'),
            'model': data.get('model', 'unknown'),
            'date': datetime.now().isoformat()
        }
        print(f"📍 Position reçue: {serial} -> {data['lat']}, {data['lng']}")
        return jsonify({"status": "ok", "serial": serial})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/locations', methods=['GET'])
def get_locations():
    """Retourne toutes les positions"""
    return jsonify(locations)

@app.route('/location/<serial>', methods=['GET'])
def get_location(serial):
    """Retourne la position d'un appareil spécifique"""
    if serial in locations:
        return jsonify(locations[serial])
    return jsonify({"status": "not_found", "serial": serial}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
