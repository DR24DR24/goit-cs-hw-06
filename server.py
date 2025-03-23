import asyncio
import logging
import websockets
import json
import names
from datetime import datetime
from pymongo import MongoClient, errors
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK

# Конфигурация
SOCKET_PORT = 5000
MONGO_URI = "mongodb+srv://rhett6butler:p123456p@rdd.fgx0a.mongodb.net/?retryWrites=true&w=majority&appName=rdd"
DB_NAME = "chatdb"
COLLECTION_NAME = "messages"

logging.basicConfig(level=logging.INFO)

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
    asyncio.run(main())
