import time
import random
import requests
import os
from faker import Faker
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import json
import asyncio
from dotenv import load_dotenv
import aiofiles

# Загружаем переменные окружения
load_dotenv()

app = FastAPI(title="Bitrix24 Contacts API")

# Получаем настройки из переменных окружения
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
WEBHOOK_URL = os.getenv("BITRIX24_WEBHOOK_URL", "https://b24-lkgkv0.bitrix24.ru/rest/1/90qyb3sbcjem26bq/")
NUM_CONTACTS = int(os.getenv("NUM_CONTACTS", 100))
NUM_COMPANIES = int(os.getenv("NUM_COMPANIES", 100))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# CORS middleware для работы с React
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fake = Faker("ru_RU")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        if not self.active_connections:
            return
            
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                disconnected.append(connection)
        
        # Удаляем отключенные соединения
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

class Contact(BaseModel):
    id: Optional[int] = None
    name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    post: Optional[str] = None
    company_id: Optional[int] = None

class Company(BaseModel):
    id: Optional[int] = None
    title: str
    phone: Optional[str] = None
    email: Optional[str] = None
    contacts: List[Contact] = []

def bx_call(method, params=None):
    url = f"{WEBHOOK_URL}{method}.json"
    try:
        resp = requests.post(url, json=params or {}, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            print(f"API Error in {method}: {data['error']}")
            return None

        return data
    except Exception as e:
        print(f"Error calling {method}: {e}")
        return None

def create_contact():
    fields = {
        "NAME": fake.first_name(),
        "LAST_NAME": fake.last_name(),
        "PHONE": [{"VALUE": fake.phone_number(), "VALUE_TYPE": "WORK"}],
        "EMAIL": [{"VALUE": fake.company_email(), "VALUE_TYPE": "WORK"}],
        "POST": fake.job()
    }
    payload = {"fields": fields, "params": {"REGISTER_SONET_EVENT": "N"}}
    res = bx_call("crm.contact.add", payload)
    result = res.get("result") if res and "result" in res else None
    return result

def create_company():
    fields = {
        "TITLE": fake.company(),
        "PHONE": [{"VALUE": fake.phone_number(), "VALUE_TYPE": "WORK"}],
        "EMAIL": [{"VALUE": fake.company_email(), "VALUE_TYPE": "WORK"}]
    }
    payload = {"fields": fields, "params": {"REGISTER_SONET_EVENT": "N"}}
    res = bx_call("crm.company.add", payload)
    result = res.get("result") if res and "result" in res else None
    return result

def link_contact_to_company(contact_id, company_id):
    try:
        payload = {
            "id": int(contact_id),
            "fields": {
                "COMPANY_ID": int(company_id)
            },
            "params": {"REGISTER_SONET_EVENT": "N"}
        }

        res = bx_call("crm.contact.update", payload)
        if res and "result" in res and res["result"]:
            return True
        else:
            return False
    except Exception as e:
        return False

async def get_all_companies():
    companies = []
    start = 0
    has_more = True

    while has_more:
        data = bx_call("crm.company.list", {
            "start": start,
            "select": ["ID", "TITLE", "PHONE", "EMAIL"]
        })

        if not data or "result" not in data:
            break

        companies.extend(data["result"])
        has_more = data.get("next") is not None
        start += 50

    return companies

async def get_contacts_for_company(company_id):
    try:
        links_data = bx_call("crm.company.contact.items.get", {
            "id": company_id
        })

        contacts = []
        for link in links_data.get("result", []):
            try:
                contact_data = bx_call("crm.contact.get", {
                    "id": link["CONTACT_ID"],
                    "select": ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL", "POST", "COMPANY_ID"]
                })
                if contact_data and "result" in contact_data:
                    contact = contact_data["result"]
                    contacts.append(Contact(
                        id=contact.get("ID"),
                        name=contact.get("NAME", ""),
                        last_name=contact.get("LAST_NAME", ""),
                        phone=contact.get("PHONE", [{}])[0].get("VALUE") if contact.get("PHONE") else None,
                        email=contact.get("EMAIL", [{}])[0].get("VALUE") if contact.get("EMAIL") else None,
                        post=contact.get("POST"),
                        company_id=contact.get("COMPANY_ID")
                    ))
            except Exception as e:
                print(f"Error loading contact {link.get('CONTACT_ID')}: {e}")
        return contacts
    except Exception as e:
        print(f"Error getting contacts for company {company_id}: {e}")
        return []

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
    await manager.connect(websocket)
    try:
        while True:
            try:
                # Ждем сообщение с таймаутом, чтобы не блокировать соединение
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                
                # Обработка ping/pong для поддержания соединения
                if data == "ping":
                    await manager.send_personal_message("pong", websocket)
                    
            except asyncio.TimeoutError:
                # Таймаут - это нормально, продолжаем слушать
                continue
            except WebSocketDisconnect:
                break
    except Exception as e:
        pass
    finally:
        manager.disconnect(websocket)

@app.post("/create-test-data")
async def create_test_data():
    """Создание тестовых данных в Bitrix24 с real-time обновлениями"""
    try:
        print("Начинаем создание тестовых данных в Битрикс 24...")
        await manager.broadcast(json.dumps({
            "type": "start",
            "message": "Начинаем создание тестовых данных в Битрикс 24..."
        }))
        
        # Сначала создаем компании (без отправки на фронтенд)
        print("\nСоздаём компании...")
        await manager.broadcast(json.dumps({
            "type": "companies_start",
            "message": "Создаём компании..."
        }))
        
        company_ids = []
        for i in range(NUM_COMPANIES):
            coid = create_company()
            if coid:
                company_ids.append(coid)
                # Отправляем прогресс каждые 10 компаний или на последней
                if len(company_ids) % 10 == 0 or len(company_ids) == NUM_COMPANIES:
                    print(f"Сгенерировано {len(company_ids)}/{NUM_COMPANIES} компаний")
                    await manager.broadcast(json.dumps({
                        "type": "companies_progress",
                        "current": len(company_ids),
                        "total": NUM_COMPANIES,
                        "message": f"Создано компаний: {len(company_ids)}/{NUM_COMPANIES}"
                    }))
            await asyncio.sleep(0.05)
        
        await manager.broadcast(json.dumps({
            "type": "companies_complete",
            "message": f"Создано компаний: {len(company_ids)}"
        }))
        
        # Перемешиваем список компаний
        random.shuffle(company_ids)
        await manager.broadcast(json.dumps({
            "type": "companies_shuffled",
            "message": "Компании перемешаны"
        }))
        
        # Теперь создаем контакты и сразу привязываем к компаниям
        await manager.broadcast(json.dumps({
            "type": "contacts_start",
            "message": "Создаём контакты и привязываем к компаниям..."
        }))
        
        contacts_per_company = NUM_CONTACTS // NUM_COMPANIES
        remainder = NUM_CONTACTS % NUM_COMPANIES
        
        
        successful_links = 0
        contact_index = 0
        
        for i, company_id in enumerate(company_ids):
            contacts_for_this_company = contacts_per_company
            if i < remainder:
                contacts_for_this_company += 1
            
            
            # Получаем данные компании для отправки на фронтенд
            company_data = bx_call("crm.company.get", {
                "id": company_id,
                "select": ["ID", "TITLE", "PHONE", "EMAIL"]
            })
            
            company_info = None
            if company_data and "result" in company_data:
                company = company_data["result"]
                company_info = {
                    "id": company.get("ID"),
                    "title": company.get("TITLE"),
                    "phone": company.get("PHONE", [{}])[0].get("VALUE") if company.get("PHONE") else None,
                    "email": company.get("EMAIL", [{}])[0].get("VALUE") if company.get("EMAIL") else None,
                    "contacts": []
                }
            
            # Флаг для отслеживания, была ли компания уже отправлена на фронтенд
            company_sent_to_frontend = False
            
            for j in range(contacts_for_this_company):
                print(f"Генерируем контакт и связываем {successful_links + 1}/{NUM_CONTACTS}")
                # Создаем контакт
                cid = create_contact()
                if cid:
                    
                    # Получаем данные контакта для отправки на фронтенд
                    contact_data = bx_call("crm.contact.get", {
                        "id": cid,
                        "select": ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL", "POST"]
                    })
                    
                    contact_info = None
                    if contact_data and "result" in contact_data:
                        contact = contact_data["result"]
                        contact_info = {
                            "id": contact.get("ID"),
                            "name": contact.get("NAME", ""),
                            "last_name": contact.get("LAST_NAME", ""),
                            "phone": contact.get("PHONE", [{}])[0].get("VALUE") if contact.get("PHONE") else None,
                            "email": contact.get("EMAIL", [{}])[0].get("VALUE") if contact.get("EMAIL") else None,
                            "post": contact.get("POST"),
                            "company_id": company_id
                        }
                    
                    # Сразу привязываем к компании
                    if link_contact_to_company(cid, company_id):
                        successful_links += 1
                        print(f"Контакт {cid} успешно связан с компанией {company_id}")
                        
                        # Добавляем контакт к компании
                        if company_info and contact_info:
                            company_info["contacts"].append(contact_info)
                        
                        # Отправляем компанию с контактом на фронтенд
                        if not company_sent_to_frontend:
                            # Первый контакт - отправляем компанию с контактом
                            await manager.broadcast(json.dumps({
                                "type": "company_with_contact",
                                "company_data": company_info,
                                "contact_data": contact_info
                            }))
                            company_sent_to_frontend = True
                        else:
                            # Последующие контакты - отправляем только контакт для добавления к существующей компании
                            await manager.broadcast(json.dumps({
                                "type": "contact_added",
                                "company_id": company_id,
                                "contact_data": contact_info
                            }))
                    else:
                        print(f"Ошибка привязки контакта {cid} к компании {company_id}")
                        await manager.broadcast(json.dumps({
                            "type": "contact_linked",
                            "contact_id": cid,
                            "company_id": company_id,
                            "success": False,
                            "contact_data": contact_info
                        }))
                    contact_index += 1
                else:
                    print(f"  ❌ Ошибка создания контакта {j + 1}")
                await asyncio.sleep(0.05)
            
            print(f"  📊 Итого для компании {company_id}: {contacts_for_this_company} контактов")
        
        print(f"\n✅ Готово! Распределение завершено:")
        print(f"📊 Статистика:")
        print(f"   - Контактов создано: {contact_index}")
        print(f"   - Компаний создано: {len(company_ids)}")
        print(f"   - Успешно привязано: {successful_links}")
        print(f"   - Контактов распределено: {contact_index}")
        
        await manager.broadcast(json.dumps({
            "type": "complete",
            "message": "✅ Готово! Распределение завершено",
            "stats": {
                "contacts_created": contact_index,
                "companies_created": len(company_ids),
                "successful_links": successful_links
            }
        }))
        
        return {
            "message": "Test data created successfully",
            "contacts_created": contact_index,
            "companies_created": len(company_ids),
            "successful_links": successful_links
        }
    except Exception as e:
        print(f"❌ Ошибка создания данных: {e}")
        await manager.broadcast(json.dumps({
            "type": "error",
            "message": f"❌ Ошибка создания данных: {e}"
        }))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/companies", response_model=List[Company])
async def get_companies():
    """Получение всех компаний с контактами"""
    try:
        print("📋 Загружаем все компании...")
        companies_data = await get_all_companies()
        print(f"✅ Найдено {len(companies_data)} компаний")
        
        companies = []
        for i, company in enumerate(companies_data):
            print(f"Обрабатываем компанию {i + 1}/{len(companies_data)}: {company['TITLE']}")
            contacts = await get_contacts_for_company(company["ID"])
            print(f"  - Найдено контактов: {len(contacts)}")
            
            company_obj = Company(
                id=company["ID"],
                title=company["TITLE"],
                phone=company.get("PHONE", [{}])[0].get("VALUE") if company.get("PHONE") else None,
                email=company.get("EMAIL", [{}])[0].get("VALUE") if company.get("EMAIL") else None,
                contacts=contacts
            )
            companies.append(company_obj)

        print(f"✅ Загружено {len(companies)} компаний с контактами")
        return companies
    except Exception as e:
        print(f"❌ Ошибка загрузки компаний: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print(f"🚀 Starting Bitrix24 Contacts API on {HOST}:{PORT}")
    print(f"📁 Frontend build path: {frontend_build_path}")
    print(f"🌐 Allowed origins: {ALLOWED_ORIGINS}")
    print(f"🔗 Bitrix24 Webhook: {'*' * 50}")  # Скрываем webhook URL
    print(f"📊 Will create {NUM_CONTACTS} contacts and {NUM_COMPANIES} companies")
    
    uvicorn.run(app, host=HOST, port=PORT, log_level="info" if DEBUG else "warning")
