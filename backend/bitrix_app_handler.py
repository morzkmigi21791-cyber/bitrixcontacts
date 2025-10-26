import json
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Dict, Any
import urllib.parse

class Bitrix24AppHandler:
    def __init__(self):
        self.placements = {
            'CRM_LEAD_LIST_MENU': 'CRM_LEAD_LIST_MENU',
            'CRM_DEAL_LIST_MENU': 'CRM_DEAL_LIST_MENU', 
            'CRM_CONTACT_LIST_MENU': 'CRM_CONTACT_LIST_MENU',
            'CRM_COMPANY_LIST_MENU': 'CRM_COMPANY_LIST_MENU',
            'CRM_LEAD_DETAIL_MENU': 'CRM_LEAD_DETAIL_MENU',
            'CRM_DEAL_DETAIL_MENU': 'CRM_DEAL_DETAIL_MENU',
            'CRM_CONTACT_DETAIL_MENU': 'CRM_CONTACT_DETAIL_MENU',
            'CRM_COMPANY_DETAIL_MENU': 'CRM_COMPANY_DETAIL_MENU'
        }
    
    def create_button_html(self, placement: str, title: str = "Bitrix24 Контакты") -> str:
        """Создает HTML для кнопки в интерфейсе Битрикс24"""
        return f"""
        <div class="bitrix24-contacts-button">
            <a href="https://amusingly-awaited-starling.cloudpub.ru" 
               target="_blank" 
               class="bitrix24-contacts-link"
               style="
                   display: inline-block;
                   padding: 8px 16px;
                   background: #2fc6f6;
                   color: white;
                   text-decoration: none;
                   border-radius: 4px;
                   font-size: 14px;
                   font-weight: 500;
                   transition: background-color 0.3s;
               "
               onmouseover="this.style.backgroundColor='#1ea8d4'"
               onmouseout="this.style.backgroundColor='#2fc6f6'">
                🏢 {title}
            </a>
        </div>
        """
    
    def create_placement_handler(self, placement: str) -> str:
        """Создает обработчик для размещения кнопки - встраивает готовый фронтенд"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Bitrix24 Контакты</title>
            <style>
                body, html {{
                    margin: 0;
                    padding: 0;
                    height: 100%;
                    overflow: hidden;
                }}
                #app-container {{
                    width: 100%;
                    height: 100vh;
                    border: none;
                }}
            </style>
        </head>
        <body>
            <iframe 
                id="app-container"
                src="https://amusingly-awaited-starling.cloudpub.ru"
                frameborder="0"
                allowfullscreen>
            </iframe>
            
            <script>
                console.log('Bitrix24 Контакты loaded in placement:', '{placement}');
                
                // Настраиваем iframe для полного отображения
                const iframe = document.getElementById('app-container');
                
                // Убираем отступы и делаем iframe на весь экран
                iframe.style.width = '100%';
                iframe.style.height = '100vh';
                iframe.style.border = 'none';
                iframe.style.margin = '0';
                iframe.style.padding = '0';
                
                // Обработка сообщений от iframe (если нужно)
                window.addEventListener('message', function(event) {{
                    if (event.origin === 'https://amusingly-awaited-starling.cloudpub.ru') {{
                        console.log('Message from iframe:', event.data);
                    }}
                }});
            </script>
        </body>
        </html>
        """

def create_app_routes(app: FastAPI):
    """Создает маршруты для интеграции с Битрикс24"""
    app_handler = Bitrix24AppHandler()
    
    @app.get("/api/bitrix24")
    async def bitrix24_handler(request: Request):
        """Основной обработчик для Битрикс24"""
        try:
            # Получаем параметры запроса
            params = dict(request.query_params)
            
            # Проверяем тип запроса
            if 'PLACEMENT' in params:
                placement = params['PLACEMENT']
                if placement in app_handler.placements:
                    # Возвращаем HTML для размещения кнопки
                    html_content = app_handler.create_placement_handler(placement)
                    return HTMLResponse(html_content)
            
            # Если это не запрос на размещение, возвращаем основное приложение
            return HTMLResponse("""
            <html>
                <head>
                    <title>Bitrix24 Контакты</title>
                    <meta charset="utf-8">
                    <style>
                        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
                        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                        .header { text-align: center; margin-bottom: 30px; }
                        .header h1 { color: #2fc6f6; margin: 0; }
                        .header p { color: #666; margin: 10px 0 0 0; }
                        .btn { 
                            background: #2fc6f6; color: white; border: none; padding: 12px 24px; 
                            border-radius: 4px; cursor: pointer; font-size: 16px; 
                            transition: background-color 0.3s;
                        }
                        .btn:hover { background: #1ea8d4; }
                        .btn:disabled { background: #ccc; cursor: not-allowed; }
                        .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
                        .status.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                        .status.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
                        .status.loading { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
                        .loading-spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid #f3f3f3; border-top: 2px solid #2fc6f6; border-radius: 50%; animation: spin 1s linear infinite; margin-right: 8px; }
                        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>🏢 Bitrix24 Контакты</h1>
                            <p>Управление компаниями и контактами</p>
                        </div>
                        
                        <div style="text-align: center; margin: 40px 0;">
                            <button class="btn" onclick="openApp()">
                                Открыть приложение
                            </button>
                        </div>
                        
                        <div style="text-align: center; color: #666;">
                            <p>Приложение интегрировано с Битрикс24</p>
                            <p>Используйте кнопки в интерфейсе CRM для быстрого доступа</p>
                        </div>
                    </div>
                    
                    <script>
                        function openApp() {
                            window.open('https://amusingly-awaited-starling.cloudpub.ru', '_blank');
                        }
                    </script>
                </body>
            </html>
            """)
            
        except Exception as e:
            return HTMLResponse(f"""
            <html>
                <head><title>Ошибка</title></head>
                <body>
                    <h1>Ошибка обработки запроса</h1>
                    <p>{str(e)}</p>
                </body>
            </html>
            """, status_code=500)
    
    @app.get("/api/bitrix24/button_handler")
    @app.post("/api/bitrix24/button_handler")
    async def button_handler(request: Request):
        """Обработчик для кнопок в интерфейсе Битрикс24"""
        try:
            # Получаем параметры из query или body
            if request.method == "GET":
                params = dict(request.query_params)
            else:  # POST
                try:
                    body = await request.json()
                    params = body
                except:
                    params = dict(request.query_params)
            
            placement = params.get('PLACEMENT', '')
            print(f"Button handler called with placement: {placement}")
            
            # Возвращаем HTML для кнопки
            html_content = app_handler.create_placement_handler(placement)
            return HTMLResponse(html_content)
            
        except Exception as e:
            print(f"Button handler error: {e}")
            return HTMLResponse(f"Ошибка: {str(e)}", status_code=500)
    
    @app.post("/api/bitrix24/webhook")
    async def webhook_handler(request: Request):
        """Обработчик webhook от Битрикс24"""
        try:
            data = await request.json()
            
            # Обрабатываем различные типы событий
            event_type = data.get('event', '')
            
            if event_type == 'ONCRMLEADADD':
                # Новый лид добавлен
                lead_id = data.get('data', {}).get('FIELDS', {}).get('ID')
                print(f"Новый лид добавлен: {lead_id}")
                
            elif event_type == 'ONCRMDEALADD':
                # Новая сделка добавлена
                deal_id = data.get('data', {}).get('FIELDS', {}).get('ID')
                print(f"Новая сделка добавлена: {deal_id}")
                
            elif event_type == 'ONCRMCONTACTADD':
                # Новый контакт добавлен
                contact_id = data.get('data', {}).get('FIELDS', {}).get('ID')
                print(f"Новый контакт добавлен: {contact_id}")
                
            elif event_type == 'ONCRMCOMPANYADD':
                # Новая компания добавлена
                company_id = data.get('data', {}).get('FIELDS', {}).get('ID')
                print(f"Новая компания добавлена: {company_id}")
            
            return JSONResponse({"status": "success"})
            
        except Exception as e:
            print(f"Ошибка обработки webhook: {e}")
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
