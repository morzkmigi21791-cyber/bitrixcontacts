import os
import json
import requests
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from typing import Optional
import urllib.parse
from config import BITRIX24_CLIENT_ID, BITRIX24_CLIENT_SECRET, BITRIX24_REDIRECT_URI

class Bitrix24OAuth:
    def __init__(self):
        self.client_id = BITRIX24_CLIENT_ID
        self.client_secret = BITRIX24_CLIENT_SECRET
        self.redirect_uri = BITRIX24_REDIRECT_URI
        self.auth_url = "https://oauth.bitrix.info/oauth/authorize/"
        self.token_url = "https://oauth.bitrix.info/oauth/token/"
        
    def get_auth_url(self, domain: str) -> str:
        """Генерирует URL для авторизации"""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'crm,user',
            'state': domain
        }
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}"
    
    def get_access_token(self, code: str, domain: str) -> dict:
        """Получает токен доступа"""
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'code': code,
            'scope': 'crm,user'
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка получения токена: {e}")
    
    def refresh_access_token(self, refresh_token: str) -> dict:
        """Обновляет токен доступа"""
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка обновления токена: {e}")

# Глобальный экземпляр OAuth
oauth = Bitrix24OAuth()

def create_oauth_routes(app: FastAPI):
    """Создает маршруты для OAuth авторизации"""
    
    @app.get("/bitrix/oauth/install")
    async def install_app(request: Request):
        domain = request.query_params.get('DOMAIN')

        # Если домен не указан — просто ничего не проверяем, используем дефолтное значение или пустое
        if not domain:
            domain = ''

        # Генерируем ссылку на авторизацию и сразу редиректим
        auth_url = oauth.get_auth_url(domain)
        return RedirectResponse(url=auth_url)




    
    @app.get("/bitrix/oauth/callback")
    async def oauth_callback(
        code: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        error: Optional[str] = Query(None)
    ):
        """Обработчик callback от Битрикс24"""
        if error:
            return HTMLResponse(f"""
            <html>
                <head><title>Ошибка авторизации</title></head>
                <body>
                    <h1>Ошибка авторизации</h1>
                    <p>Ошибка: {error}</p>
                </body>
            </html>
            """, status_code=400)
        
        if not code or not state:
            return HTMLResponse("""
            <html>
                <head><title>Ошибка авторизации</title></head>
                <body>
                    <h1>Ошибка авторизации</h1>
                    <p>Отсутствует код авторизации или состояние</p>
                </body>
            </html>
            """, status_code=400)
        
        try:
            # Получаем токены
            tokens = oauth.get_access_token(code, state)
            
            # Сохраняем токены (в реальном приложении - в базе данных)
            # Здесь просто возвращаем успешную страницу
            return HTMLResponse(f"""
            <html>
                <head>
                    <title>Успешная установка</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                        .success {{ color: #28a745; }}
                        .info {{ color: #17a2b8; margin: 20px 0; }}
                        .button {{ 
                            background: #007bff; color: white; padding: 10px 20px; 
                            border: none; border-radius: 5px; cursor: pointer; 
                            text-decoration: none; display: inline-block; margin: 10px;
                        }}
                        .progress {{ 
                            background: #f8f9fa; border: 1px solid #dee2e6; 
                            border-radius: 5px; padding: 20px; margin: 20px 0; 
                        }}
                        .progress-bar {{ 
                            background: #28a745; height: 20px; border-radius: 10px; 
                            transition: width 0.3s; margin: 10px 0;
                        }}
                        .status {{ margin: 10px 0; padding: 10px; border-radius: 5px; }}
                        .status.success {{ background: #d4edda; color: #155724; }}
                        .status.error {{ background: #f8d7da; color: #721c24; }}
                        .status.info {{ background: #d1ecf1; color: #0c5460; }}
                    </style>
                </head>
                <body>
                    <h1 class="success">🎉 Приложение успешно установлено!</h1>
                    <p class="info">Домен: {state}</p>
                    <p class="info">Токен доступа получен</p>
                    
                    <div class="progress">
                        <h3>🔗 Добавление кнопок в интерфейс Битрикс24</h3>
                        <div class="progress-bar" id="progressBar" style="width: 0%;"></div>
                        <div id="progressText">0%</div>
                        <div id="statusMessages"></div>
                    </div>
                    
                    <div>
                        <button class="button" onclick="openApp()">🏢 Открыть приложение</button>
                        <button class="button" onclick="retryButtons()" id="retryBtn" style="display: none;">🔄 Повторить добавление кнопок</button>
                    </div>
                    
                    <script>
                        const domain = '{state}';
                        const accessToken = '{tokens.get("access_token", "")}';
                        const placements = [
                            {{ name: 'CRM_LEAD_LIST_MENU', title: 'Список лидов' }},
                            {{ name: 'CRM_DEAL_LIST_MENU', title: 'Список сделок' }},
                            {{ name: 'CRM_CONTACT_LIST_MENU', title: 'Список контактов' }},
                            {{ name: 'CRM_COMPANY_LIST_MENU', title: 'Список компаний' }},
                            {{ name: 'CRM_LEAD_DETAIL_MENU', title: 'Карточка лида' }},
                            {{ name: 'CRM_DEAL_DETAIL_MENU', title: 'Карточка сделки' }},
                            {{ name: 'CRM_CONTACT_DETAIL_MENU', title: 'Карточка контакта' }},
                            {{ name: 'CRM_COMPANY_DETAIL_MENU', title: 'Карточка компании' }}
                        ];
                        
                        let successCount = 0;
                        let totalCount = placements.length;
                        
                        function addStatusMessage(message, type = 'info') {{
                            const statusDiv = document.getElementById('statusMessages');
                            const messageDiv = document.createElement('div');
                            messageDiv.className = `status ${{type}}`;
                            messageDiv.textContent = message;
                            statusDiv.appendChild(messageDiv);
                        }}
                        
                        function updateProgress(current, total) {{
                            const percentage = Math.round((current / total) * 100);
                            document.getElementById('progressBar').style.width = `${{percentage}}%`;
                            document.getElementById('progressText').textContent = `${{percentage}}% (${{current}}/${{total}})`;
                        }}
                        
                        async function addPlacement(placement, index) {{
                            try {{
                                const url = `https://${{domain}}/rest/1/${{accessToken}}/placement.bind.json`;
                                const data = {{
                                    PLACEMENT: placement.name,
                                    HANDLER: 'https://amusingly-awaited-starling.cloudpub.ru/api/bitrix24/button_handler',
                                    TITLE: 'Bitrix24 Контакты'
                                }};
                                
                                const response = await fetch(url, {{
                                    method: 'POST',
                                    headers: {{ 'Content-Type': 'application/json' }},
                                    body: JSON.stringify(data)
                                }});
                                
                                const result = await response.json();
                                
                                if (result.error) {{
                                    addStatusMessage(`❌ ${{placement.title}}: ${{result.error.description}}`, 'error');
                                }} else {{
                                    successCount++;
                                    addStatusMessage(`✅ ${{placement.title}}: добавлена`, 'success');
                                }}
                                
                                updateProgress(index + 1, totalCount);
                                
                                if (index === totalCount - 1) {{
                                    // Все размещения обработаны
                                    if (successCount > 0) {{
                                        addStatusMessage(`🎉 Успешно добавлено ${{successCount}} из ${{totalCount}} кнопок!`, 'success');
                                        addStatusMessage('Обновите страницы в Битрикс24, чтобы увидеть кнопки.', 'info');
                                    }} else {{
                                        addStatusMessage('❌ Не удалось добавить кнопки. Проверьте права доступа.', 'error');
                                        document.getElementById('retryBtn').style.display = 'inline-block';
                                    }}
                                    
                                    // Автоматически закрываем окно через 5 секунд
                                    setTimeout(() => {{
                                        window.close();
                                    }}, 5000);
                                }}
                                
                            }} catch (error) {{
                                addStatusMessage(`❌ ${{placement.title}}: ошибка сети`, 'error');
                                updateProgress(index + 1, totalCount);
                            }}
                        }}
                        
                        function openApp() {{
                            window.open('https://amusingly-awaited-starling.cloudpub.ru', '_blank');
                        }}
                        
                        function retryButtons() {{
                            document.getElementById('statusMessages').innerHTML = '';
                            document.getElementById('retryBtn').style.display = 'none';
                            successCount = 0;
                            updateProgress(0, totalCount);
                            
                            placements.forEach((placement, index) => {{
                                setTimeout(() => addPlacement(placement, index), index * 500);
                            }});
                        }}
                        
                        // Автоматически начинаем добавление кнопок
                        window.onload = function() {{
                            addStatusMessage('🚀 Начинаем добавление кнопок в интерфейс...', 'info');
                            
                            placements.forEach((placement, index) => {{
                                setTimeout(() => addPlacement(placement, index), index * 500);
                            }});
                        }};
                    </script>
                </body>
            </html>
            """)
            
        except Exception as e:
            return HTMLResponse(f"""
            <html>
                <head><title>Ошибка установки</title></head>
                <body>
                    <h1>Ошибка установки</h1>
                    <p>Ошибка: {str(e)}</p>
                </body>
            </html>
            """, status_code=500)
