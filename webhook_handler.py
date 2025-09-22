#!/usr/bin/env python3
"""
GitHub Webhook Handler für sofortiges Deployment
Läuft parallel zur PM2-basierten Lösung für noch schnellere Updates
"""

import os
import sys
import json
import hmac
import hashlib
import subprocess
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

# Konfiguration
WEBHOOK_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET', 'your-webhook-secret')
DEPLOY_SCRIPT = '/home/ochtii/pimic/deploy.sh'
PORT = 8080

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ochtii/pimic/display/webhook.log'),
        logging.StreamHandler()
    ]
)

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/webhook':
            self.send_response(404)
            self.end_headers()
            return

        # Payload lesen
        content_length = int(self.headers.get('Content-Length', 0))
        payload = self.rfile.read(content_length)
        
        # Signature prüfen
        signature = self.headers.get('X-Hub-Signature-256', '')
        if not self.verify_signature(payload, signature):
            logging.warning("Invalid signature received")
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'Unauthorized')
            return

        try:
            # JSON parsen
            data = json.loads(payload.decode('utf-8'))
            
            # Nur auf Push-Events auf master branch reagieren
            if (data.get('ref') == 'refs/heads/master' and 
                data.get('repository', {}).get('name') == 'virtual_network_microphone'):
                
                logging.info("Valid push to master detected, triggering deployment")
                
                # Deployment-Script ausführen
                result = subprocess.run(
                    ['/bin/bash', DEPLOY_SCRIPT],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 Minuten Timeout
                )
                
                if result.returncode == 0:
                    logging.info("Deployment completed successfully")
                    response = "Deployment successful"
                    status = 200
                else:
                    logging.error(f"Deployment failed: {result.stderr}")
                    response = f"Deployment failed: {result.stderr}"
                    status = 500
                    
            else:
                logging.info("Ignoring push (not master branch or wrong repo)")
                response = "Ignored (not master branch)"
                status = 200
                
        except Exception as e:
            logging.error(f"Error processing webhook: {e}")
            response = f"Error: {e}"
            status = 500

        self.send_response(status)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(response.encode())

    def verify_signature(self, payload, signature):
        """GitHub Webhook Signature verifizieren"""
        if not signature.startswith('sha256='):
            return False
            
        expected = hmac.new(
            WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f'sha256={expected}', signature)

    def log_message(self, format, *args):
        """Logging überschreiben"""
        logging.info(format % args)

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), WebhookHandler)
    logging.info(f"Starting webhook server on port {PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down webhook server")
        server.shutdown()