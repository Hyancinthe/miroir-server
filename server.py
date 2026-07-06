from flask import Flask, request, jsonify
from datetime import datetime
import os

app = Flask(__name__)
locations = {}
signatures = {}  # Nouveau : stockage des signatures DNS

@app.route('/')
def home():
    return jsonify({
        "service": "Miroir Tracker", 
        "agents": len(locations), 
        "signatures": len(signatures),
        "status": "online"
    })

@app.route('/report', methods=['POST'])
def report():
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
        return jsonify({"status": "ok", "serial": serial})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# ===== NOUVEAU : Route pour les signatures DNS =====
@app.route('/dns/signature', methods=['POST'])
def dns_signature():
    """
    Reçoit la signature de l'agent via HTTP (au lieu de DNS)
    L'agent envoie : {"signature": "MIROIR_7BA1CD77"}
    """
    try:
        data = request.get_json()
        signature = data.get('signature', 'unknown')
        ip_source = request.remote_addr
        
        if signature in signatures:
            signatures[signature]['count'] += 1
        else:
            signatures[signature] = {
                'count': 1,
                'first_seen': datetime.now().isoformat()
            }
        
        signatures[signature].update({
            'signature': signature,
            'ip': ip_source,
            'model': data.get('model', 'unknown'),
            'last_seen': datetime.now().isoformat()
        })
        
        print(f"📡 Signature reçue: {signature} | IP: {ip_source}")
        return jsonify({"status": "ok", "signature": signature})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/dns/signatures', methods=['GET'])
def get_signatures():
    """Retourne toutes les signatures capturées"""
    return jsonify(signatures)

@app.route('/dns/signature/<signature>', methods=['GET'])
def get_signature(signature):
    """Retourne une signature spécifique"""
    if signature in signatures:
        return jsonify(signatures[signature])
    return jsonify({"status": "not_found"}), 404

@app.route('/locations', methods=['GET'])
def get_locations():
    return jsonify(locations)

@app.route('/location/<serial>', methods=['GET'])
def get_location(serial):
    if serial in locations:
        return jsonify(locations[serial])
    return jsonify({"status": "not_found"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)