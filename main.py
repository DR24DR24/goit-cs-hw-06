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

# Конфігурація
HTTP_PORT = 3000
SOCKET_PORT = 5000
MONGO_URI = "mongodb://mongo:27017/chatdb"
DB_NAME = "chatdb"
COLLECTION_NAME = "messages"



logging.basicConfig(level=logging.INFO)

# HTTP-сервер
class HTTPServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.path = "/index.html"
        elif self.path == "/message":
            self.path = "/message.html"
        elif self.path == "/style.css":
            self.path = "/style.css"
        elif self.path == "/logo.png":
            self.path = "/logo.png"
        else:
            self.path = "/error.html"
        return super().do_GET()

def start_http_server():
    with socketserver.TCPServer(("", HTTP_PORT), HTTPServerHandler) as httpd:
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
    asyncio.run(main())
