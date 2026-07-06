from flask import Flask, request, jsonify
from datetime import datetime
import os
import requests

app = Flask(__name__)
locations = {}
signatures = {}

def geolocaliser_ip(ip):
    """Géolocalise une IP gratuitement via ip-api.com"""
    try:
        # IP locales = position par défaut (Madagascar)
        if ip == '127.0.0.1' or ip.startswith('192.168.') or ip.startswith('10.'):
            return -18.9137, 47.5361, "Local", "Madagascar", "Madagascar"
        
        url = f"http://ip-api.com/json/{ip}?fields=lat,lon,city,country,countryCode"
        r = requests.get(url, timeout=5)
        data = r.json()
        return (
            data.get('lat'), 
            data.get('lng'), 
            data.get('city', 'Inconnu'), 
            data.get('country', 'Inconnu'),
            data.get('countryCode', '??')
        )
    except:
        return None, None, "Inconnu", "Inconnu", "??"

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

@app.route('/dns/signature', methods=['POST'])
def dns_signature():
    """
    Reçoit la signature de l'agent via HTTP
    L'agent envoie : {"signature": "MIROIR_7BA1CD77", "model": "Redmi 5A"}
    Retourne la position géolocalisée par IP
    """
    try:
        data = request.get_json()
        signature = data.get('signature', 'unknown')
        model = data.get('model', 'unknown')
        ip_source = request.remote_addr
        
        # Géolocalisation par IP
        lat, lng, city, country, country_code = geolocaliser_ip(ip_source)
        
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
            'model': model,
            'lat': lat,
            'lng': lng,
            'city': city,
            'country': country,
            'country_code': country_code,
            'precision': 5000,
            'source': 'Signature DNS',
            'last_seen': datetime.now().isoformat()
        })
        
        print(f"📡 Signature: {signature} | IP: {ip_source} | {city}, {country}")
        return jsonify({
            "status": "ok", 
            "signature": signature,
            "location": {
                "lat": lat,
                "lng": lng,
                "city": city,
                "country": country
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/dns/signatures', methods=['GET'])
def get_signatures():
    """Retourne toutes les signatures avec leur position"""
    return jsonify(signatures)

@app.route('/dns/signature/<signature>', methods=['GET'])
def get_signature(signature):
    """Retourne une signature spécifique avec sa position"""
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