"""Local-only launcher; bind first, then open the browser."""
import functools
import http.server
import json
from pathlib import Path
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent.parent
URL = 'http://127.0.0.1:8765/viewer/'
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
try:
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 8765), handler)
except OSError:
    try:
        with urllib.request.urlopen('http://127.0.0.1:8765/assets/living/scene.json', timeout=2) as response:
            meta = json.load(response)
        if meta.get('source') != 'island_dusk_refined.blend':
            raise ValueError('Another project is using this port')
    except Exception:
        raise SystemExit('端口 8765 已被占用。请关闭占用该端口的服务，或从终端选择另一个端口。')
    webbrowser.open(URL)
else:
    print('暮光浮岛：' + URL + '\n关闭此窗口或按 Ctrl+C 停止服务器。', flush=True)
    webbrowser.open(URL)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
