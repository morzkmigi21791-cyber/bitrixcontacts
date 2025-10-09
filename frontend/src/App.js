import React, { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [statusType, setStatusType] = useState('');
  const [wsConnected, setWsConnected] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [progress, setProgress] = useState({ current: 0, total: 0, type: '' });
  const [connectionNotification, setConnectionNotification] = useState('');
  const [isInitialConnection, setIsInitialConnection] = useState(true);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const maxReconnectAttempts = 3;
  const reconnectDelay = 5000; // 5 секунд между попытками

  // Функция для показа временного уведомления
  const showConnectionNotification = (message, type = 'info') => {
    setConnectionNotification({ message, type });
    setTimeout(() => {
      setConnectionNotification('');
    }, 3000); // Показываем 3 секунды
  };

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
      // Определяем WebSocket URL в зависимости от окружения
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost = window.location.host;
      const ws = new WebSocket(`${wsProtocol}//${wsHost}/ws`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setWsConnected(true);
        setReconnectAttempts(0);
        
        // Показываем уведомление только если это не первоначальное подключение
        if (!isInitialConnection) {
          showConnectionNotification('✅ Подключено к серверу', 'success');
        }
        setIsInitialConnection(false);
        
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
        setWsConnected(false);
        showConnectionNotification('❌ Отключено от сервера', 'error');
        
        // Очищаем ping интервал
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        
        if (reconnectAttempts < maxReconnectAttempts) {
          showConnectionNotification(`🔄 Переподключение... (${reconnectAttempts + 1}/${maxReconnectAttempts})`, 'loading');
          reconnectTimeoutRef.current = setTimeout(() => {
            setReconnectAttempts(prev => prev + 1);
            connectWebSocket();
          }, reconnectDelay);
        } else {
          showConnectionNotification('❌ Не удалось подключиться к серверу', 'error');
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        showConnectionNotification('❌ Ошибка подключения к серверу', 'error');
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
    }
  };

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'start':
        setStatus(data.message);
        setStatusType('loading');
        break;
      case 'companies_start':
        setStatus(data.message);
        setProgress({ current: 0, total: 100, type: 'companies' });
        break;
      case 'companies_progress':
        setProgress({ current: data.current, total: data.total, type: 'companies' });
        setStatus(data.message);
        break;
      case 'company_created':
        setStatus(`🏢 Создана компания ${data.company_id} (${data.progress})`);
        break;
      case 'companies_complete':
        setStatus(data.message);
        setProgress({ current: data.total || 100, total: data.total || 100, type: 'companies' });
        break;
      case 'companies_shuffled':
        setStatus(data.message);
        break;
      case 'contacts_start':
        setStatus(data.message);
        break;
      case 'company_processing':
        setStatus(`📱 Обрабатываем компанию ${data.company_index}/${data.total_companies} (ID: ${data.company_id})`);
        break;
      case 'company_with_contact':
        // Добавляем новую компанию с первым контактом
        setCompanies(prev => [...prev, data.company_data]);
        setStatus(`✅ Компания ${data.company_data.title} создана с контактом ${data.contact_data.name} ${data.contact_data.last_name}`);
        break;
      case 'contact_added':
        // Добавляем контакт к существующей компании
        setCompanies(prev => prev.map(company => {
          if (company.id === data.company_id) {
            return {
              ...company,
              contacts: [...company.contacts, data.contact_data]
            };
          }
          return company;
        }));
        setStatus(`✅ Контакт ${data.contact_data.name} ${data.contact_data.last_name} добавлен к компании`);
        break;
      case 'contact_linked':
        if (!data.success) {
          setStatus(`❌ Ошибка привязки контакта ${data.contact_id} к компании ${data.company_id}`);
        }
        break;
      case 'complete':
        setStatus(data.message);
        setStatusType('success');
        setLoading(false);
        setProgress({ current: 0, total: 0, type: '' });
        break;
      case 'error':
        setStatus(data.message);
        setStatusType('error');
        setLoading(false);
        setProgress({ current: 0, total: 0, type: '' });
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  };

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
    if (!wsConnected) {
      setStatus('❌ Нет подключения к серверу. Попробуйте перезагрузить страницу.');
      setStatusType('error');
      return;
    }

    setLoading(true);
    setStatus('Создание тестовых данных...');
    setStatusType('loading');
    
    // Очищаем список компаний перед началом создания
    setCompanies([]);

    try {
      const response = await fetch('/create-test-data', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Ошибка создания данных');
      }

      // WebSocket будет обрабатывать обновления в реальном времени
      // Не нужно здесь обрабатывать ответ, так как все обновления приходят через WebSocket
    } catch (error) {
      setStatus(`❌ Ошибка: ${error.message}`);
      setStatusType('error');
      setLoading(false);
    }
  };

  // Removed automatic data loading on startup

  return (
    <div className="container">
      {/* Уведомление о подключении */}
      {connectionNotification && (
        <div className={`connection-notification ${connectionNotification.type}`}>
          {connectionNotification.message}
        </div>
      )}

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
          {progress.total > 0 && progress.type === 'companies' && (
            <div className="progress-container">
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${(progress.current / progress.total) * 100}%` }}
                ></div>
              </div>
              <div className="progress-text">
                {progress.current}/{progress.total} компаний
              </div>
            </div>
          )}
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
