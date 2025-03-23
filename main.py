import asyncio
import logging
import websockets
import json
import names
from datetime import datetime
from pymongo import MongoClient, errors
import http.server
import socketserver
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# Конфігурація
HTTP_PORT = 3000
SOCKET_PORT = 5000
MONGO_URI = "mongodb://mongo:27017/chatdb"
DB_NAME = "chatdb"
COLLECTION_NAME = "messages"

logging.basicConfig(level=logging.INFO)

# HTTP-сервер
class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == "/":
            self.send_html_file("index.html")
        elif pr_url.path == "/message.html":
            self.send_html_file("message.html")
        elif pr_url.path == "/style.css":
            self.send_html_file("style.css")
        elif pr_url.path == "/logo.png":
            self.send_html_file("logo.png")
        else:
            self.send_html_file("error.html", 404)
            
    def do_POST(self):
        if self.path == "/message":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode("utf-8")
            post_params = urllib.parse.parse_qs(post_data)
            
            username = post_params.get("username", [""])[0]
            message = post_params.get("message", [""])[0]
            data = {"date": datetime.now().isoformat(), "username": username, "message": message}
            
            try:
                client = MongoClient(MONGO_URI)
                db = client[DB_NAME]
                collection = db[COLLECTION_NAME]
                collection.insert_one(data)
                self.send_response(200)
            except errors.PyMongoError as e:
                logging.error(f"Error inserting data into MongoDB: {e}")
                self.send_response(500)
            
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Message received and stored.")        

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        try:
            with open(filename, "rb") as fd:
                self.wfile.write(fd.read())
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

def start_http_server():
    server_address = ("", HTTP_PORT)
    httpd = HTTPServer(server_address, HttpHandler)
    logging.info(f"HTTP Server running on port {HTTP_PORT}")
    httpd.serve_forever()


class Server:
    clients = set()
    
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
    except errors.PyMongoError as e:
        logging.error(f"Error connecting to MongoDB: {e}")
        collection = None

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connects')

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnects')

    async def send_to_clients(self, message: str):
        if self.clients:
            await asyncio.wait([client.send(message) for client in self.clients])

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distribute(ws)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

    async def distribute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            data = json.loads(message)
            data["date"] = datetime.now().isoformat()
            if self.collection:
                self.collection.insert_one(data)
            await self.send_to_clients(f"{ws.name}: {message}")

async def main():
    server = Server()
    async with websockets.serve(server.ws_handler, '', SOCKET_PORT):
        await asyncio.Future()

if __name__ == '__main__':
    threading.Thread(target=start_http_server, daemon=True).start()
    #threading.Thread(target=start_http_server, daemon=True).start()
    asyncio.run(main())
