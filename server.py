#!/usr/bin/env python3
"""Simple dev server for Drie Kamers: serves static files + handles media uploads."""

import os
import http.server
import json
import cgi
import re

PORT = 8000
MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media')

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/upload':
            self._handle_upload()
        elif self.path == '/save-config':
            self._handle_save_config()
        else:
            self.send_error(404)

    def _handle_upload(self):
        content_type = self.headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type:
            self.send_error(400, 'Expected multipart/form-data')
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': content_type}
        )

        file_item = form['file']
        if not file_item.filename:
            self._json_response(400, {'error': 'No file provided'})
            return

        # Sanitize filename: keep only safe characters
        filename = os.path.basename(file_item.filename)
        filename = re.sub(r'[^\w.\-]', '_', filename)

        # Avoid overwriting: add suffix if file exists
        base, ext = os.path.splitext(filename)
        dest = os.path.join(MEDIA_DIR, filename)
        counter = 1
        while os.path.exists(dest):
            filename = f'{base}_{counter}{ext}'
            dest = os.path.join(MEDIA_DIR, filename)
            counter += 1

        os.makedirs(MEDIA_DIR, exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(file_item.file.read())

        rel_path = f'media/{filename}'
        print(f'  Uploaded: {rel_path} ({os.path.getsize(dest)} bytes)')
        self._json_response(200, {'path': rel_path, 'filename': filename})

    def _handle_save_config(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            cfg = json.loads(body)
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media-config.json')
            with open(config_path, 'w') as f:
                json.dump(cfg, f, indent=2)
            print(f'  Config saved: {config_path}')
            self._json_response(200, {'ok': True})
        except Exception as e:
            self._json_response(500, {'error': str(e)})

    def _json_response(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f'Serving at http://localhost:{PORT}')
    print(f'Media folder: {MEDIA_DIR}')
    http.server.HTTPServer(('', PORT), Handler).serve_forever()
