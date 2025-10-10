import time
import asyncio
import uuid
from typing import List, Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_sessions: Dict[str, dict] = {}  # session_id -> {websocket, generation_active, generation_paused, etc.}
        # Убираем глобальные флаги - теперь все индивидуально
        self.last_activity = time.time()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        session_id = str(uuid.uuid4())
        
        # Создаем индивидуальную сессию пользователя
        self.user_sessions[session_id] = {
            'websocket': websocket,
            'generation_active': False,
            'generation_paused': False,
            'generation_task': None,
            'pause_start_time': None,
            'last_activity': time.time(),
            'generation_initiator': False  # Флаг того, кто инициировал генерацию
        }
        
        self.active_connections.append(websocket)
        self.last_activity = time.time()
        
        return session_id

    async def connect_with_session_id(self, websocket: WebSocket, session_id: str):
        """Подключает WebSocket с предопределенным session_id"""
        # Создаем индивидуальную сессию пользователя
        self.user_sessions[session_id] = {
            'websocket': websocket,
            'generation_active': False,
            'generation_paused': False,
            'generation_task': None,
            'pause_start_time': None,
            'last_activity': time.time(),
            'generation_initiator': False  # Флаг того, кто инициировал генерацию
        }
        
        self.active_connections.append(websocket)
        self.last_activity = time.time()
        
        return session_id

    def disconnect(self, websocket: WebSocket):
        # Находим и удаляем сессию пользователя
        session_to_remove = None
        session_data_to_remove = None
        
        for session_id, session_data in self.user_sessions.items():
            if session_data['websocket'] == websocket:
                session_to_remove = session_id
                session_data_to_remove = session_data
                break
        
        if session_to_remove and session_data_to_remove:
            # Если у этого пользователя была активная генерация, останавливаем её
            if session_data_to_remove['generation_active']:
                print(f"Генерация отменена для сессии {session_to_remove[:8]} - пользователь отключился")
                session_data_to_remove['generation_active'] = False
                session_data_to_remove['generation_paused'] = False
                if session_data_to_remove['generation_task'] and not session_data_to_remove['generation_task'].done():
                    session_data_to_remove['generation_task'].cancel()
            
            del self.user_sessions[session_to_remove]
        
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
        self.last_activity = time.time()

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
            self.last_activity = time.time()
        except Exception as e:
            self.disconnect(websocket)

    async def send_message_to_session(self, session_id: str, message: str):
        """Отправляет сообщение конкретной сессии"""
        if session_id in self.user_sessions:
            session_data = self.user_sessions[session_id]
            try:
                await session_data['websocket'].send_text(message)
                session_data['last_activity'] = time.time()
                self.last_activity = time.time()
            except Exception as e:
                print(f"Ошибка отправки сообщения сессии {session_id}: {e}")
                self.disconnect(session_data['websocket'])

    async def broadcast(self, message: str):
        if not self.active_connections:
            return
            
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
                self.last_activity = time.time()
            except Exception as e:
                disconnected.append(connection)
        
        # Удаляем отключенные соединения
        for conn in disconnected:
            self.disconnect(conn)

    def has_active_connections(self) -> bool:
        """Проверяет, есть ли активные соединения"""
        return len(self.active_connections) > 0

    def get_session_by_websocket(self, websocket: WebSocket):
        """Получает сессию по WebSocket"""
        for session_id, session_data in self.user_sessions.items():
            if session_data['websocket'] == websocket:
                return session_id, session_data
        return None, None

    def get_active_sessions_count(self) -> int:
        """Возвращает количество активных сессий"""
        return len(self.user_sessions)

    def has_any_active_generation(self) -> bool:
        """Проверяет, есть ли активная генерация у любого пользователя"""
        return any(session['generation_active'] for session in self.user_sessions.values())

    def get_generation_status(self) -> dict:
        """Возвращает статус генерации"""
        active_sessions = sum(1 for session in self.user_sessions.values() if session['generation_active'])
        paused_sessions = sum(1 for session in self.user_sessions.values() if session['generation_paused'])
        
        return {
            "has_connections": len(self.active_connections) > 0,
            "active_sessions": len(self.user_sessions),
            "active_generations": active_sessions,
            "paused_generations": paused_sessions
        }

    def get_session_generation_status(self, session_id: str) -> dict:
        """Возвращает статус генерации для конкретной сессии"""
        if session_id not in self.user_sessions:
            return {"error": "Session not found"}
        
        session_data = self.user_sessions[session_id]
        return {
            "generation_active": session_data['generation_active'],
            "generation_paused": session_data['generation_paused'],
            "generation_initiator": session_data['generation_initiator']
        }

    def should_stop_generation_for_session(self, session_id: str) -> bool:
        """Проверяет, нужно ли остановить генерацию для конкретной сессии"""
        if session_id not in self.user_sessions:
            return True
        
        session_data = self.user_sessions[session_id]
        if not session_data['generation_active']:
            return False
        
        # Если генерация приостановлена более 15 секунд
        if session_data['generation_paused'] and session_data['pause_start_time']:
            return time.time() - session_data['pause_start_time'] > 15
        
        return False

    def is_generation_paused_for_session(self, session_id: str) -> bool:
        """Проверяет, приостановлена ли генерация для конкретной сессии"""
        if session_id not in self.user_sessions:
            return False
        return self.user_sessions[session_id]['generation_paused']

    async def wait_for_resume_for_session(self, session_id: str):
        """Ожидает возобновления генерации для конкретной сессии"""
        while (session_id in self.user_sessions and 
               self.user_sessions[session_id]['generation_paused'] and 
               self.user_sessions[session_id]['generation_active']):
            await asyncio.sleep(0.5)  # Проверяем каждые 500мс

    async def stop_generation_for_session(self, session_id: str):
        """Останавливает генерацию для конкретной сессии"""
        if session_id in self.user_sessions:
            session_data = self.user_sessions[session_id]
            if session_data['generation_task'] and not session_data['generation_task'].done():
                session_data['generation_task'].cancel()
            if session_data['generation_active']:
                print(f"Генерация отменена для сессии {session_id[:8]} - остановка по запросу")
            session_data['generation_active'] = False
            session_data['generation_paused'] = False
            session_data['generation_initiator'] = False

    def start_generation_for_session(self, session_id: str):
        """Запускает генерацию для конкретной сессии"""
        if session_id in self.user_sessions:
            self.user_sessions[session_id]['generation_active'] = True
            self.user_sessions[session_id]['generation_paused'] = False
            self.user_sessions[session_id]['generation_initiator'] = True
            self.user_sessions[session_id]['pause_start_time'] = None
