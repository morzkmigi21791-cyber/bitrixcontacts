import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [statusType, setStatusType] = useState('');

  const createTestData = async () => {
    setLoading(true);
    setStatus('Создание тестовых данных...');
    setStatusType('loading');

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

      const data = await response.json();
      setStatus(`✅ Данные созданы! Контактов: ${data.contacts_created}, Компаний: ${data.companies_created}, Связей: ${data.successful_links}`);
      setStatusType('success');
      
      // Загружаем обновленные данные
      await loadCompanies();
    } catch (error) {
      setStatus(`❌ Ошибка: ${error.message}`);
      setStatusType('error');
    } finally {
      setLoading(false);
    }
  };

  const loadCompanies = async () => {
    setLoading(true);
    setStatus('Загрузка компаний...');
    setStatusType('loading');

    try {
      const response = await fetch('/companies');
      if (!response.ok) {
        throw new Error('Ошибка загрузки данных');
      }

      const data = await response.json();
      setCompanies(data);
      setStatus(`✅ Загружено ${data.length} компаний`);
      setStatusType('success');
    } catch (error) {
      setStatus(`❌ Ошибка: ${error.message}`);
      setStatusType('error');
    } finally {
      setLoading(false);
    }
  };

  // Removed automatic data loading on startup

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
        <button 
          className="btn btn-secondary" 
          onClick={loadCompanies} 
          disabled={loading}
        >
          {loading && <span className="loading-spinner"></span>}
          Загрузить данные
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
