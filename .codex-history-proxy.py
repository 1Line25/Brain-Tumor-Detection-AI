from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).parent
FRONTEND = ROOT / "frontend"


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        clean_path = path.split("?", 1)[0].lstrip("/") or "index.html"
        if clean_path.startswith("storage/"):
            return str(ROOT / clean_path)
        return str(FRONTEND / clean_path)

    def proxy(self):
        target = f"http://127.0.0.1:8001{self.path}"
        body_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(body_length) if body_length else None
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() in {"authorization", "content-type"}
        }
        request = Request(target, data=body, headers=headers, method=self.command)
        try:
            response = urlopen(request, timeout=30)
        except HTTPError as error:
            response = error

        response_body = response.read()
        self.send_response(response.status)
        self.send_header(
            "Content-Type",
            response.headers.get("Content-Type", "application/json"),
        )
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self.proxy()
        return super().do_GET()

    def do_POST(self):
        return self.proxy()

    def do_PATCH(self):
        return self.proxy()


ThreadingHTTPServer(("127.0.0.1", 8768), Handler).serve_forever()
