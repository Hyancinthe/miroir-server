from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
import os
import requests

app = Flask(__name__)
locations = {}
signatures = {}
position_history = []  # Historique des positions

def geolocaliser_ip(ip):
    try:
        if ip == '127.0.0.1' or ip.startswith('192.168.') or ip.startswith('10.'):
            return -18.9137, 47.5361, "Local", "Madagascar", "Madagascar"
        url = f"http://ip-api.com/json/{ip}?fields=lat,lon,city,country,countryCode"
        r = requests.get(url, timeout=5)
        data = r.json()
        return (data.get('lat'), data.get('lng'), data.get('city', 'Inconnu'), 
                data.get('country', 'Inconnu'), data.get('countryCode', '??'))
    except:
        return None, None, "Inconnu", "Inconnu", "??"

@app.route('/')
def home():
    return render_template_string(HOME_TEMPLATE)

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
        # Ajouter à l'historique
        position_history.append({
            'serial': serial,
            'lat': data['lat'],
            'lng': data['lng'],
            'precision': data.get('precision', 0),
            'source': data.get('source', 'agent'),
            'model': data.get('model', 'unknown'),
            'date': datetime.now().isoformat()
        })
        # Garder les 100 dernières positions
        if len(position_history) > 100:
            position_history.pop(0)
        return jsonify({"status": "ok", "serial": serial})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/dns/signature', methods=['POST'])
def dns_signature():
    try:
        data = request.get_json()
        signature = data.get('signature', 'unknown')
        model = data.get('model', 'unknown')
        ip_source = request.remote_addr
        
        lat, lng, city, country, country_code = geolocaliser_ip(ip_source)
        
        if signature in signatures:
            signatures[signature]['count'] += 1
        else:
            signatures[signature] = {'count': 1, 'first_seen': datetime.now().isoformat()}
        
        signatures[signature].update({
            'signature': signature, 'ip': ip_source, 'model': model,
            'lat': lat, 'lng': lng, 'city': city, 'country': country,
            'country_code': country_code, 'precision': 5000,
            'source': 'Signature DNS', 'last_seen': datetime.now().isoformat()
        })
        
        # Ajouter à l'historique des positions
        position_history.append({
            'serial': signature,
            'lat': lat, 'lng': lng,
            'precision': 5000,
            'source': 'Signature DNS',
            'model': model,
            'date': datetime.now().isoformat()
        })
        if len(position_history) > 100:
            position_history.pop(0)
        
        print(f"📡 Signature: {signature} | IP: {ip_source} | {city}, {country}")
        return jsonify({"status": "ok", "signature": signature})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/positions', methods=['GET'])
def get_positions():
    """Retourne toutes les positions récentes pour la carte"""
    return jsonify({
        'locations': locations,
        'signatures': signatures,
        'history': position_history[-50:]  # 50 dernières positions
    })

@app.route('/dns/signatures', methods=['GET'])
def get_signatures():
    return jsonify(signatures)

@app.route('/dns/signature/<signature>', methods=['GET'])
def get_signature(signature):
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

# Template HTML avec carte temps réel
HOME_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Miroir Tracker - Temps réel</title>
    <meta http-equiv="refresh" content="30">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #1a1a2e; color: #eee; }
        .header { background: #16213e; padding: 20px; text-align: center; border-bottom: 2px solid #FF9500; }
        .header h1 { color: #FF9500; font-size: 28px; }
        .header span { color: #34C759; font-size: 14px; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .status-bar { background: #0f3460; padding: 15px; border-radius: 10px; margin-bottom: 20px; display: flex; justify-content: space-around; }
        .stat { text-align: center; }
        .stat-number { font-size: 32px; font-weight: bold; color: #FF9500; }
        .stat-label { font-size: 12px; color: #aaa; }
        #map { height: 500px; border-radius: 10px; margin-bottom: 20px; border: 2px solid #FF9500; }
        .device-card { background: #0f3460; border-radius: 10px; padding: 15px; margin-bottom: 10px; border-left: 4px solid #FF9500; }
        .device-card h3 { color: #FF9500; margin-bottom: 8px; }
        .device-card p { color: #aaa; font-size: 13px; margin: 3px 0; }
        .device-card .coords { color: #34C759; font-weight: bold; }
        .refresh { color: #FF9500; font-size: 11px; text-align: center; margin-top: 10px; }
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
</head>
<body>
    <div class="header">
        <h1>🛡️ Miroir Tracker</h1>
        <span>Suivi en temps réel • Auto-refresh 30s</span>
    </div>
    <div class="container">
        <div class="status-bar" id="status">
            <div class="stat"><div class="stat-number" id="agentCount">-</div><div class="stat-label">Agents actifs</div></div>
            <div class="stat"><div class="stat-number" id="sigCount">-</div><div class="stat-label">Signatures</div></div>
            <div class="stat"><div class="stat-number pulse">🟢</div><div class="stat-label">En ligne</div></div>
        </div>
        <div id="map"></div>
        <div id="devices"><div style="text-align:center;color:#aaa;padding:20px;">Chargement...</div></div>
        <div class="refresh">🔄 Auto-refresh toutes les 30 secondes • Dernière mise à jour : <span id="lastUpdate">-</span></div>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([-18.9137, 47.5361], 6);
        L.tileLayer('https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga', {maxZoom:22}).addTo(map);
        
        var markers = [];
        
        function loadData() {
            fetch('/api/positions')
                .then(r => r.json())
                .then(data => {
                    // Clear old markers
                    markers.forEach(m => map.removeLayer(m));
                    markers = [];
                    
                    var bounds = [];
                    
                    // Afficher les locations
                    for (var serial in data.locations) {
                        var loc = data.locations[serial];
                        var marker = L.marker([loc.lat, loc.lng])
                            .addTo(map)
                            .bindPopup('<b>📱 ' + loc.model + '</b><br>📍 ' + loc.lat.toFixed(6) + ', ' + loc.lng.toFixed(6) + '<br>📡 ' + loc.source + ' (±' + loc.precision + 'm)<br>🕐 ' + loc.date);
                        L.circle([loc.lat, loc.lng], {color: '#34C759', fillColor: '#34C759', fillOpacity: 0.2, radius: loc.precision}).addTo(map);
                        markers.push(marker);
                        bounds.push([loc.lat, loc.lng]);
                    }
                    
                    // Afficher les signatures
                    for (var sig in data.signatures) {
                        var s = data.signatures[sig];
                        if (s.lat && s.lng && s.ip != '127.0.0.1') {
                            var marker = L.marker([s.lat, s.lng], {
                                icon: L.divIcon({className: '', html: '<div style="background:#FF9500;width:14px;height:14px;border-radius:50%;border:2px solid white;"></div>'})
                            }).addTo(map).bindPopup('<b>🔑 ' + sig + '</b><br>📍 ' + s.lat.toFixed(6) + ', ' + s.lng.toFixed(6) + '<br>🏙️ ' + s.city + ', ' + s.country + '<br>🔄 x' + s.count);
                            markers.push(marker);
                            bounds.push([s.lat, s.lng]);
                        }
                    }
                    
                    if (bounds.length > 0) {
                        map.fitBounds(bounds, {padding: [50, 50]});
                    }
                    
                    document.getElementById('agentCount').textContent = Object.keys(data.locations).length;
                    document.getElementById('sigCount').textContent = Object.keys(data.signatures).length;
                    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
                    
                    // Afficher la liste des appareils
                    var html = '';
                    for (var serial in data.locations) {
                        var loc = data.locations[serial];
                        html += '<div class="device-card">';
                        html += '<h3>📱 ' + loc.model + '</h3>';
                        html += '<p>S/N: ' + serial + '</p>';
                        html += '<p class="coords">📍 ' + loc.lat.toFixed(6) + ', ' + loc.lng.toFixed(6) + '</p>';
                        html += '<p>📡 ' + loc.source + ' | Précision: ±' + loc.precision + 'm</p>';
                        html += '<p>🕐 ' + loc.date + '</p>';
                        html += '</div>';
                    }
                    for (var sig in data.signatures) {
                        var s = data.signatures[sig];
                        html += '<div class="device-card" style="border-left-color: #FF9500;">';
                        html += '<h3>🔑 ' + sig + ' <span style="font-size:11px;color:#aaa;">(Signature)</span></h3>';
                        html += '<p>📱 ' + s.model + '</p>';
                        if (s.lat) html += '<p class="coords">📍 ' + s.lat.toFixed(6) + ', ' + s.lng.toFixed(6) + '</p>';
                        html += '<p>🏙️ ' + s.city + ', ' + s.country + '</p>';
                        html += '<p>🔄 Détecté x' + s.count + ' | 🕐 ' + s.last_seen + '</p>';
                        html += '</div>';
                    }
                    document.getElementById('devices').innerHTML = html || '<div style="text-align:center;color:#aaa;padding:20px;">Aucun appareil</div>';
                });
        }
        
        loadData();
        setInterval(loadData, 30000);
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)