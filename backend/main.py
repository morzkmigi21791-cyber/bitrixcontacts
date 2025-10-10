import os
import json
import asyncio
import random
import requests
import time
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List
import uvicorn

from config import PORT, HOST, DEBUG, ALLOWED_ORIGINS, NUM_CONTACTS, NUM_COMPANIES, WEBHOOK_URL
from models import Company, CreateTestDataRequest
from websocket_manager import ConnectionManager
from data_generator import create_companies_batch_import, create_contacts_batch_import, update_contacts_company_batch, create_one_to_one_links
from bitrix_api import bx_call

app = FastAPI(title="Bitrix24 Contacts API")

# CORS middleware для работы с React
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()

def get_generated_data_batch(company_ids, contact_ids):
    """Получает сгенерированные компании и контакты через batch API батчами по 20"""
    try:
        print(f"Загружаем {len(company_ids)} компаний и {len(contact_ids)} контактов через batch API...")
        
        batch_size = 20
        companies_data = {}
        contacts_data = {}
        
        # Загружаем компании батчами
        for batch_start in range(0, len(company_ids), batch_size):
            batch_end = min(batch_start + batch_size, len(company_ids))
            batch_company_ids = company_ids[batch_start:batch_end]
            
            company_commands = {}
            for i, company_id in enumerate(batch_company_ids):
                company_commands[f"company_{batch_start + i}"] = f"crm.company.get?id={company_id}&select[0]=ID&select[1]=TITLE&select[2]=PHONE&select[3]=EMAIL"
            
            batch_companies = execute_batch_request(company_commands, "компании")
            companies_data.update(batch_companies)
            
            time.sleep(0.1)  # Небольшая пауза между батчами
        
        # Загружаем контакты батчами
        for batch_start in range(0, len(contact_ids), batch_size):
            batch_end = min(batch_start + batch_size, len(contact_ids))
            batch_contact_ids = contact_ids[batch_start:batch_end]
            
            contact_commands = {}
            for i, contact_id in enumerate(batch_contact_ids):
                contact_commands[f"contact_{batch_start + i}"] = f"crm.contact.get?id={contact_id}&select[0]=ID&select[1]=NAME&select[2]=LAST_NAME&select[3]=PHONE&select[4]=EMAIL&select[5]=POST&select[6]=COMPANY_ID"
            
            batch_contacts = execute_batch_request(contact_commands, "контакты")
            contacts_data.update(batch_contacts)
            
            time.sleep(0.1)  # Небольшая пауза между батчами
        
        print(f"Получено {len(companies_data)} компаний и {len(contacts_data)} контактов")
        
        # Создаем объекты компаний с контактами
        companies = []
        for key, company in companies_data.items():
            company_id = company["ID"]
            
            # Находим контакты для этой компании
            company_contacts = []
            for contact_key, contact in contacts_data.items():
                if contact.get("COMPANY_ID") == company_id:
                    company_contacts.append({
                        "id": contact.get("ID"),
                        "name": contact.get("NAME", ""),
                        "last_name": contact.get("LAST_NAME", ""),
                        "phone": contact.get("PHONE", [{}])[0].get("VALUE") if contact.get("PHONE") else None,
                        "email": contact.get("EMAIL", [{}])[0].get("VALUE") if contact.get("EMAIL") else None,
                        "post": contact.get("POST"),
                        "company_id": contact.get("COMPANY_ID")
                    })
            
            company_obj = Company(
                id=company["ID"],
                title=company["TITLE"],
                phone=company.get("PHONE", [{}])[0].get("VALUE") if company.get("PHONE") else None,
                email=company.get("EMAIL", [{}])[0].get("VALUE") if company.get("EMAIL") else None,
                contacts=company_contacts
            )
            companies.append(company_obj)
        
        print(f"Создано {len(companies)} объектов компаний с контактами")
        return companies
        
    except Exception as e:
        print(f"Ошибка batch загрузки данных: {e}")
        return []

def execute_batch_request(commands, entity_type):
    """Выполняет batch запрос и возвращает результаты"""
    try:
        url = f"{WEBHOOK_URL}batch.json"
        payload = {"halt": 0, "cmd": commands}
        
        resp = requests.post(url, json=payload, timeout=60)
        
        if resp.status_code != 200:
            print(f"Batch request HTTP Error {resp.status_code}: {resp.text}")
            return {}
            
        response_data = resp.json()
        
        if "error" in response_data:
            print(f"Batch request Error: {response_data['error']}")
            return {}
        
        results = response_data.get("result", {}).get("result", {})
        
        # Обрабатываем результаты - value уже содержит данные напрямую
        processed_data = {}
        for key, value in results.items():
            if value:
                processed_data[key] = value
        
        print(f"Получено {len(processed_data)} {entity_type} из batch")
        return processed_data
        
    except Exception as e:
        print(f"Ошибка выполнения batch запроса для {entity_type}: {e}")
        return {}

# Обслуживание статических файлов фронтенда
frontend_build_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "build")
if os.path.exists(frontend_build_path):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_build_path, "static")), name="static")
    
    @app.get("/")
    async def serve_frontend():
        """Обслуживание главной страницы React приложения"""
        return FileResponse(os.path.join(frontend_build_path, "index.html"))
    
    @app.get("/favicon.ico")
    async def favicon():
        """Обслуживание favicon"""
        favicon_path = os.path.join(frontend_build_path, "favicon.ico")
        if os.path.exists(favicon_path):
            return FileResponse(favicon_path)
        return {"message": "No favicon"}
    
    # Обслуживание всех остальных маршрутов фронтенда
    @app.get("/{full_path:path}")
    async def serve_frontend_routes(full_path: str):
        """Обслуживание всех маршрутов React приложения"""
        # Проверяем, существует ли файл
        file_path = os.path.join(frontend_build_path, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        # Если файл не найден, возвращаем index.html для SPA
        return FileResponse(os.path.join(frontend_build_path, "index.html"))
else:
    @app.get("/")
    async def root():
        return {"message": "Bitrix24 Contacts API", "frontend": "Not built yet. Run 'npm run build' in frontend directory"}
    
    @app.get("/favicon.ico")
    async def favicon():
        return {"message": "No favicon"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = None
    
    try:
        while True:
            try:
                # Ждем сообщение с таймаутом, чтобы не блокировать соединение
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                
                # Обработка ping/pong для поддержания соединения
                if data == "ping":
                    await manager.send_personal_message("pong", websocket)
                elif data.startswith("session_id:"):
                    # Получаем session_id от клиента
                    session_id = data.split(":", 1)[1]
                    await manager.connect_with_session_id(websocket, session_id)
                    
            except asyncio.TimeoutError:
                # Таймаут - это нормально, продолжаем слушать
                continue
            except WebSocketDisconnect:
                break
    except Exception as e:
        print(f"WebSocket error for session {session_id}: {e}")
    finally:
        if session_id:
            manager.disconnect(websocket)

@app.post("/create-test-data")
async def create_test_data(request: CreateTestDataRequest):
    """Создание тестовых данных в Bitrix24 с real-time обновлениями"""
    try:
        session_id = request.session_id
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID required")
        
        # Проверяем, существует ли сессия
        if session_id not in manager.user_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Убираем глобальную блокировку - она блокирует всех пользователей
        # Каждый пользователь должен иметь возможность запускать свою генерацию независимо
        
        # Проверяем, не запущена ли уже генерация для этой сессии
        session_data = manager.user_sessions[session_id]
        if session_data['generation_active']:
            if session_data['generation_paused']:
                raise HTTPException(status_code=409, detail="Генерация приостановлена. Подключитесь для возобновления.")
            else:
                # Возвращаем информацию о текущем статусе вместо ошибки
                return {
                    "message": "Генерация уже запущена для этой сессии",
                    "status": "already_running",
                    "session_id": session_id[:8]
                }
        
        # Запускаем генерацию для конкретной сессии
        manager.start_generation_for_session(session_id)
        print(f"Начинаем создание тестовых данных в Битрикс 24: Сессия {session_id[:8]}...")
        
        # Сначала создаем контакты через batch import
        print(f"Создаём {NUM_CONTACTS} контактов: Сессия {session_id[:8]}...")
        
        # Проверяем соединение перед началом
        if manager.should_stop_generation_for_session(session_id):
            await manager.stop_generation_for_session(session_id)
            raise HTTPException(status_code=408, detail="Сессия неактивна")
        
        # Создаем контакты батчами по 20 (ограничение batch import)
        contact_ids = []
        batch_size = 20
        for batch_start in range(0, NUM_CONTACTS, batch_size):
            batch_end = min(batch_start + batch_size, NUM_CONTACTS)
            batch_count = batch_end - batch_start
            
            # Проверяем соединение перед каждым батчем
            if manager.should_stop_generation_for_session(session_id):
                await manager.stop_generation_for_session(session_id)
                raise HTTPException(status_code=408, detail="Сессия неактивна")
            
            # Если генерация приостановлена, ждем возобновления
            if manager.is_generation_paused_for_session(session_id):
                print(f"Ожидание возобновления генерации для сессии {session_id}...")
                await manager.wait_for_resume_for_session(session_id)
            
            print(f"Создаем контакты {batch_start + 1}-{batch_end}: Сессия {session_id[:8]}...")
            batch_contacts = create_contacts_batch_import(batch_count)
            contact_ids.extend([cid for cid in batch_contacts if cid])
            
            await asyncio.sleep(0.2)  # Пауза между батчами для избежания лимитов
        
        print(f"Создано контактов: {len(contact_ids)}")
        
        # Теперь создаем компании через batch import
        print(f"Создаём {NUM_COMPANIES} компаний: Сессия {session_id[:8]}...")
        
        # Проверяем соединение перед созданием компаний
        if manager.should_stop_generation_for_session(session_id):
            await manager.stop_generation_for_session(session_id)
            raise HTTPException(status_code=408, detail="Сессия неактивна")
        
        # Создаем компании батчами по 20 (ограничение batch import)
        company_ids = []
        for batch_start in range(0, NUM_COMPANIES, batch_size):
            batch_end = min(batch_start + batch_size, NUM_COMPANIES)
            batch_count = batch_end - batch_start
            
            # Проверяем соединение перед каждым батчем
            if manager.should_stop_generation_for_session(session_id):
                await manager.stop_generation_for_session(session_id)
                raise HTTPException(status_code=408, detail="Сессия неактивна")
            
            # Если генерация приостановлена, ждем возобновления
            if manager.is_generation_paused_for_session(session_id):
                print(f"Ожидание возобновления генерации для сессии {session_id}...")
                await manager.wait_for_resume_for_session(session_id)
            
            print(f"Создаем компании {batch_start + 1}-{batch_end}: Сессия {session_id[:8]}...")
            batch_companies = create_companies_batch_import(batch_count)
            company_ids.extend([cid for cid in batch_companies if cid])
            
            await asyncio.sleep(0.2)  # Пауза между батчами для избежания лимитов
        
        print(f"Создано компаний: {len(company_ids)}")
        
        # Создаем случайные пары контакт-компания (1 к 1)
        print(f"Создаем случайные пары контакт-компания (1 к 1): Сессия {session_id[:8]}...")
        
        # Создаем пары 1 к 1
        links = create_one_to_one_links(contact_ids, company_ids)
        
        # Привязываем контакты батчами по 20
        successful_links = 0
        for batch_start in range(0, len(links), batch_size):
            batch_end = min(batch_start + batch_size, len(links))
            batch_links = links[batch_start:batch_end]
            
            # Проверяем соединение перед каждым батчем
            if manager.should_stop_generation_for_session(session_id):
                await manager.stop_generation_for_session(session_id)
                raise HTTPException(status_code=408, detail="Сессия неактивна")
            
            # Если генерация приостановлена, ждем возобновления
            if manager.is_generation_paused_for_session(session_id):
                print(f"Ожидание возобновления генерации для сессии {session_id}...")
                await manager.wait_for_resume_for_session(session_id)
            
            print(f"Привязываем контакты {batch_start + 1}-{batch_end}: Сессия {session_id[:8]}...")
            batch_results = update_contacts_company_batch(batch_links)
            successful_links += len(batch_results)
            
            await asyncio.sleep(0.2)  # Пауза между батчами для избежания лимитов
        
        print(f"Готово! Статистика для сессии {session_id[:8]}:")
        print(f"Контактов создано: {len(contact_ids)}")
        print(f"Компаний создано: {len(company_ids)}")
        print(f"Успешно привязано: {successful_links}")
        
        # Загружаем сгенерированные компании с контактами через batch API
        print("Загружаем сгенерированные компании через batch API...")
        generated_companies = get_generated_data_batch(company_ids, contact_ids)
        
        # Отправляем результат только конкретной сессии
        await manager.send_message_to_session(session_id, json.dumps({
            "type": "complete",
            "message": "Готово! Случайная привязка завершена",
            "companies": [company.model_dump() for company in generated_companies]
        }))
        
        # Останавливаем генерацию для этой сессии
        await manager.stop_generation_for_session(session_id)
        
        return {
            "message": "Test data created successfully",
            "contacts_created": len(contact_ids),
            "companies_created": len(company_ids),
            "successful_links": successful_links
        }
    except Exception as e:
        if session_id in manager.user_sessions:
            print(f"Генерация отменена для сессии {session_id[:8]} - ошибка: {e}")
            await manager.stop_generation_for_session(session_id)
            await manager.send_message_to_session(session_id, json.dumps({
                "type": "error",
                "message": f"❌ Ошибка создания данных: {e}"
            }))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/generation-status")
async def get_generation_status():
    """Получение общего статуса генерации"""
    return manager.get_generation_status()

@app.get("/generation-status/{session_id}")
async def get_session_generation_status(session_id: str):
    """Получение статуса генерации для конкретной сессии"""
    return manager.get_session_generation_status(session_id)

@app.get("/session-info")
async def get_session_info():
    """Получение информации о сессиях"""
    return {
        "active_sessions": manager.get_active_sessions_count(),
        "has_connections": manager.has_active_connections(),
        "any_active_generation": manager.has_any_active_generation()
    }

if __name__ == "__main__":
    print(f"🚀 Starting Bitrix24 Contacts API on {HOST}:{PORT}")
    print(f"📁 Frontend build path: {frontend_build_path}")
    print(f"🌐 Allowed origins: {ALLOWED_ORIGINS}")
    print(f"🔗 Bitrix24 Webhook: {'*' * 50}")  # Скрываем webhook URL
    print(f"📊 Will create {NUM_CONTACTS} contacts and {NUM_COMPANIES} companies")
    
    uvicorn.run(app, host=HOST, port=PORT, log_level="info" if DEBUG else "warning")
