from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
import os
import requests

app = Flask(__name__)
locations = {}
signatures = {}
commands = {}
position_history = []

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
        position_history.append(locations[serial].copy())
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
        
        position_history.append({
            'serial': signature, 'lat': lat, 'lng': lng,
            'precision': 5000, 'source': 'Signature DNS',
            'model': model, 'date': datetime.now().isoformat()
        })
        if len(position_history) > 100:
            position_history.pop(0)
        
        return jsonify({"status": "ok", "signature": signature})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/command/<serial>', methods=['POST'])
def send_command(serial):
    """Reçoit une commande pour un appareil (alarm, lock)"""
    data = request.get_json()
    action = data.get('action')
    if action in ['alarm', 'lock']:
        commands[serial] = {
            'action': action,
            'timestamp': datetime.now().isoformat()
        }
        return jsonify({"status": "ok", "message": f"Commande {action} envoyée"})
    return jsonify({"status": "error"}), 400

@app.route('/command/<serial>', methods=['GET'])
def get_command(serial):
    """L'agent vérifie s'il y a une commande en attente"""
    if serial in commands:
        cmd = commands.pop(serial)
        return jsonify(cmd)
    return jsonify({"action": "none"})

@app.route('/api/positions', methods=['GET'])
def get_positions():
    return jsonify({
        'locations': locations,
        'signatures': signatures,
        'history': position_history[-50:]
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
        .btn { padding: 10px 16px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 12px; margin: 3px; }
        .btn-alarm { background: #FF3B30; color: white; }
        .btn-lock { background: #FF9500; color: white; }
        .refresh { color: #FF9500; font-size: 11px; text-align: center; margin-top: 10px; }
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
            <div class="stat"><div class="stat-number" id="agentCount">-</div><div class="stat-label">Agents</div></div>
            <div class="stat"><div class="stat-number" id="sigCount">-</div><div class="stat-label">Signatures</div></div>
            <div class="stat"><div class="stat-number" style="color:#34C759;">🟢</div><div class="stat-label">En ligne</div></div>
        </div>
        <div id="map"></div>
        <div id="devices">Chargement...</div>
        <div class="refresh">🔄 Auto-refresh 30s • <span id="lastUpdate">-</span></div>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([-18.9137, 47.5361], 6);
        L.tileLayer('https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga', {maxZoom:22}).addTo(map);
        var markers = [];
        
        function sendCommand(serial, action) {
            fetch('/command/' + serial, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: action})
            }).then(r => r.json()).then(d => alert(d.message));
        }
        
        function loadData() {
            fetch('/api/positions')
                .then(r => r.json())
                .then(data => {
                    markers.forEach(m => map.removeLayer(m));
                    markers = [];
                    var bounds = [];
                    
                    for (var serial in data.locations) {
                        var loc = data.locations[serial];
                        L.marker([loc.lat, loc.lng]).addTo(map)
                            .bindPopup('<b>📱 ' + loc.model + '</b><br>📍 ' + loc.lat.toFixed(6) + ', ' + loc.lng.toFixed(6) + '<br>📡 ' + loc.source + ' (±' + loc.precision + 'm)<br>🕐 ' + loc.date);
                        L.circle([loc.lat, loc.lng], {color: '#34C759', fillColor: '#34C759', fillOpacity: 0.2, radius: loc.precision}).addTo(map);
                        bounds.push([loc.lat, loc.lng]);
                    }
                    
                    if (bounds.length > 0) map.fitBounds(bounds, {padding: [50, 50]});
                    
                    document.getElementById('agentCount').textContent = Object.keys(data.locations).length;
                    document.getElementById('sigCount').textContent = Object.keys(data.signatures).length;
                    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
                    
                    var html = '';
                    for (var serial in data.locations) {
                        var loc = data.locations[serial];
                        html += '<div class="device-card">';
                        html += '<h3>📱 ' + loc.model + '</h3>';
                        html += '<p>S/N: ' + serial + '</p>';
                        html += '<p class="coords">📍 ' + loc.lat.toFixed(6) + ', ' + loc.lng.toFixed(6) + '</p>';
                        html += '<p>📡 ' + loc.source + ' | Précision: ±' + loc.precision + 'm</p>';
                        html += '<p>🕐 ' + loc.date + '</p>';
                        html += '<button class="btn btn-alarm" onclick="sendCommand(\'' + serial + '\',\'alarm\')">🚨 Faire sonner</button>';
                        html += '<button class="btn btn-lock" onclick="sendCommand(\'' + serial + '\',\'lock\')">🔒 Verrouiller</button>';
                        html += '</div>';
                    }
                    document.getElementById('devices').innerHTML = html || 'Aucun appareil';
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