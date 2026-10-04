from fastapi import WebSocket
from typing import List
import logging
import json

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Nuevo cliente WebSocket conectado. Total activos: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Cliente WebSocket desconectado. Total activos: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Difundir mensaje JSON a todos los navegadores conectados en tiempo real"""
        payload = json.dumps(message)
        logger.info(f"Difundiendo evento WebSocket a {len(self.active_connections)} clientes: {payload}")
        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.error(f"Error enviando websocket a cliente: {e}")
                self.disconnect(connection)

ws_manager = ConnectionManager()
