import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import stateManager from './stateManager';

function App() {
  // Используем централизованное состояние
  const [companies, setCompanies] = useState(stateManager.getValue('companies') || []);
  const [loading, setLoading] = useState(stateManager.getValue('loading') || false);
  const [status, setStatus] = useState(stateManager.getValue('status') || '');
  const [statusType, setStatusType] = useState(stateManager.getValue('statusType') || '');
  const [wsConnected, setWsConnected] = useState(stateManager.getValue('wsConnected') || false);
  const [reconnectAttempts, setReconnectAttempts] = useState(stateManager.getValue('reconnectAttempts') || 0);
  const [sessionId, setSessionId] = useState(stateManager.getValue('sessionId') || null);
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const maxReconnectAttempts = 3;
  const reconnectDelay = 5000; // 5 секунд между попытками

  // WebSocket connection functions
  const connectWebSocket = () => {
    // Предотвращаем создание множественных соединений
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }
    
    // Закрываем старое соединение если оно есть
    if (wsRef.current) {
      wsRef.current.close();
    }
    
    try {
      // Определяем WebSocket URL динамически
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.hostname;
      const port = window.location.port || (window.location.protocol === 'https:' ? '443' : '8000');
      const wsUrl = `${protocol}//${host}:${port}/ws`;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        stateManager.setWsConnected(true);
        stateManager.setReconnectAttempts(0);
        
        // Получаем session_id из URL или создаем новый
        const urlParams = new URLSearchParams(window.location.search);
        let currentSessionId = urlParams.get('session_id');
        
        if (!currentSessionId) {
          // Если нет session_id в URL, генерируем новый UUID и обновляем URL
          currentSessionId = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
          });
          const newUrl = new URL(window.location);
          newUrl.searchParams.set('session_id', currentSessionId);
          window.history.replaceState({}, '', newUrl);
        }
        
        stateManager.setSessionId(currentSessionId);
        console.log('Session ID:', currentSessionId);
        
        // Отправляем session_id серверу
        ws.send(`session_id:${currentSessionId}`);
        
        // Проверяем статус генерации при подключении
        checkGenerationStatus(currentSessionId);
        
        // Отправляем ping для проверки соединения
        ws.send('ping');
        
        // Устанавливаем периодические ping сообщения каждые 30 секунд
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const data = event.data;
          
          // Обработка pong ответа
          if (data === 'pong') {
            return;
          }
          
          // Обработка JSON сообщений
          const parsedData = JSON.parse(data);
          handleWebSocketMessage(parsedData);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        stateManager.setWsConnected(false);
        
        // Очищаем ping интервал
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        
        if (reconnectAttempts < maxReconnectAttempts) {
          reconnectTimeoutRef.current = setTimeout(() => {
            stateManager.setReconnectAttempts(reconnectAttempts + 1);
            connectWebSocket();
          }, reconnectDelay);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
    }
  };

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'complete':
        stateManager.setStatus(data.message, 'success');
        stateManager.setLoading(false);
        
        // Устанавливаем сгенерированные компании из WebSocket сообщения
        if (data.companies) {
          stateManager.setCompanies(data.companies);
        }
        break;
      case 'error':
        stateManager.setStatus(data.message, 'error');
        stateManager.setLoading(false);
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  };

  // Подписка на изменения централизованного состояния
  useEffect(() => {
    const unsubscribeCompanies = stateManager.subscribe('companies', setCompanies);
    const unsubscribeLoading = stateManager.subscribe('loading', setLoading);
    const unsubscribeStatus = stateManager.subscribe('status', (data) => {
      setStatus(data.status);
      setStatusType(data.statusType);
    });
    const unsubscribeWsConnected = stateManager.subscribe('wsConnected', setWsConnected);
    const unsubscribeReconnectAttempts = stateManager.subscribe('reconnectAttempts', setReconnectAttempts);
    const unsubscribeSessionId = stateManager.subscribe('sessionId', setSessionId);

    return () => {
      unsubscribeCompanies();
      unsubscribeLoading();
      unsubscribeStatus();
      unsubscribeWsConnected();
      unsubscribeReconnectAttempts();
      unsubscribeSessionId();
    };
  }, []);

  // Auto-connect WebSocket on component mount
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const createTestData = async () => {
    if (!sessionId) {
      stateManager.setStatus('❌ Ошибка: Нет активной сессии', 'error');
      return;
    }

    stateManager.setLoading(true);
    stateManager.setStatus('Создание тестовых данных...', 'loading');
    
    // Очищаем список компаний перед началом создания
    stateManager.setCompanies([]);

    try {
      const response = await fetch(`${window.location.protocol}//${window.location.host}/create-test-data`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Ошибка создания данных');
      }

      const responseData = await response.json();
      
      // Если генерация уже запущена, показываем информационное сообщение
      if (responseData.status === 'already_running') {
        stateManager.setStatus('Генерация уже запущена в другой вкладке. Ожидайте результатов...', 'loading');
        stateManager.setLoading(true);
        return;
      }

      // WebSocket будет обрабатывать обновления в реальном времени
      // Не нужно здесь обрабатывать ответ, так как все обновления приходят через WebSocket
    } catch (error) {
      stateManager.setStatus(`❌ Ошибка: ${error.message}`, 'error');
      stateManager.setLoading(false);
    }
  };

  const checkGenerationStatus = async (currentSessionId) => {
    if (!currentSessionId) return;
    
    try {
      const response = await fetch(`${window.location.protocol}//${window.location.host}/generation-status/${currentSessionId}`);
      if (response.ok) {
        const status = await response.json();
        
        if (status.generation_active) {
          if (status.generation_paused) {
            stateManager.setStatus('Генерация приостановлена. Ожидание возобновления...', 'loading');
            stateManager.setLoading(true);
          } else {
            stateManager.setStatus('Генерация данных в процессе...', 'loading');
            stateManager.setLoading(true);
          }
        }
      }
    } catch (error) {
      console.error('Ошибка проверки статуса генерации:', error);
    }
  };

  return (
    <div className="container">
      <div className="header">
        <h1>🏢 Bitrix24 Контакты</h1>
        <p>Управление компаниями и контактами</p>
      </div>

      <div className="controls">
        <button 
          className="btn" 
          onClick={createTestData} 
          disabled={loading}
        >
          {loading && <span className="loading-spinner"></span>}
          Создать тестовые данные
        </button>
      </div>

      {status && (
        <div className={`status ${statusType}`}>
          {status}
        </div>
      )}

      <div className="companies-grid">
        {companies.map((company) => (
          <div key={company.id} className="company-card">
            <div className="company-header">
              <div className="company-icon">🏢</div>
              <div>
                <h3 className="company-title">{company.title}</h3>
                <p className="company-id">ID: {company.id}</p>
              </div>
            </div>

            <div className="company-info">
              {company.phone && (
                <div className="info-item">
                  <span className="info-icon">📞</span>
                  <span>{company.phone}</span>
                </div>
              )}
              {company.email && (
                <div className="info-item">
                  <span className="info-icon">✉️</span>
                  <span>{company.email}</span>
                </div>
              )}
            </div>

            <div className="contacts-section">
              <h4 className="contacts-title">
                Контакты
                <span className="contacts-count">{company.contacts.length}</span>
              </h4>

              {company.contacts.length === 0 ? (
                <div className="no-contacts">
                  Нет контактов
                </div>
              ) : (
                <ul className="contacts-list">
                  {company.contacts.map((contact) => (
                    <li key={contact.id} className="contact-item">
                      <div className="contact-name">
                        👤 {contact.name} {contact.last_name}
                      </div>
                      <div className="contact-details">
                        {contact.phone && (
                          <div className="contact-detail">
                            📞 {contact.phone}
                          </div>
                        )}
                        {contact.email && (
                          <div className="contact-detail">
                            ✉️ {contact.email}
                          </div>
                        )}
                        {contact.post && (
                          <div className="contact-detail">
                            💼 {contact.post}
                          </div>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        ))}
      </div>

      {companies.length === 0 && !loading && (
        <div className="no-contacts" style={{ textAlign: 'center', padding: '2rem' }}>
          <h3>Нет данных</h3>
          <p>Нажмите "Создать тестовые данные" для начала работы</p>
        </div>
      )}
    </div>
  );
}

export default App;
