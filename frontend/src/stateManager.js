// Централизованное управление состоянием через BroadcastChannel
class StateManager {
  constructor() {
    this.channel = new BroadcastChannel('bitrix24-contacts');
    this.listeners = new Map();
    this.state = {
      sessionId: null,
      wsConnected: false,
      loading: false,
      status: '',
      statusType: '',
      companies: [],
      reconnectAttempts: 0
    };
    
    this.setupChannel();
  }

  setupChannel() {
    this.channel.addEventListener('message', (event) => {
      const { type, data } = event.data;
      
      switch (type) {
        case 'STATE_UPDATE':
          this.updateState(data);
          break;
        case 'SESSION_ID_SET':
          this.state.sessionId = data.sessionId;
          this.notifyListeners('sessionId', data.sessionId);
          break;
        case 'WS_CONNECTED':
          this.state.wsConnected = data.connected;
          this.notifyListeners('wsConnected', data.connected);
          break;
        case 'LOADING_STATE':
          this.state.loading = data.loading;
          this.notifyListeners('loading', data.loading);
          break;
        case 'STATUS_UPDATE':
          this.state.status = data.status;
          this.state.statusType = data.statusType;
          this.notifyListeners('status', { status: data.status, statusType: data.statusType });
          break;
        case 'COMPANIES_UPDATE':
          this.state.companies = data.companies;
          this.notifyListeners('companies', data.companies);
          break;
        case 'RECONNECT_ATTEMPTS':
          this.state.reconnectAttempts = data.attempts;
          this.notifyListeners('reconnectAttempts', data.attempts);
          break;
      }
    });
  }

  // Подписка на изменения состояния
  subscribe(key, callback) {
    if (!this.listeners.has(key)) {
      this.listeners.set(key, new Set());
    }
    this.listeners.get(key).add(callback);
    
    // Возвращаем функцию отписки
    return () => {
      const callbacks = this.listeners.get(key);
      if (callbacks) {
        callbacks.delete(callback);
      }
    };
  }

  // Уведомление слушателей
  notifyListeners(key, data) {
    const callbacks = this.listeners.get(key);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in listener for ${key}:`, error);
        }
      });
    }
  }

  // Обновление состояния
  updateState(newState) {
    Object.assign(this.state, newState);
    Object.keys(newState).forEach(key => {
      this.notifyListeners(key, newState[key]);
    });
  }

  // Методы для отправки событий
  setSessionId(sessionId) {
    this.state.sessionId = sessionId;
    this.notifyListeners('sessionId', sessionId);
    this.channel.postMessage({
      type: 'SESSION_ID_SET',
      data: { sessionId }
    });
  }

  setWsConnected(connected) {
    this.state.wsConnected = connected;
    this.notifyListeners('wsConnected', connected);
    this.channel.postMessage({
      type: 'WS_CONNECTED',
      data: { connected }
    });
  }

  setLoading(loading) {
    console.log('StateManager: setLoading', loading);
    this.state.loading = loading;
    this.notifyListeners('loading', loading);
    this.channel.postMessage({
      type: 'LOADING_STATE',
      data: { loading }
    });
  }

  setStatus(status, statusType) {
    console.log('StateManager: setStatus', status, statusType);
    this.state.status = status;
    this.state.statusType = statusType;
    this.notifyListeners('status', { status, statusType });
    this.channel.postMessage({
      type: 'STATUS_UPDATE',
      data: { status, statusType }
    });
  }

  setCompanies(companies) {
    this.state.companies = companies;
    this.notifyListeners('companies', companies);
    this.channel.postMessage({
      type: 'COMPANIES_UPDATE',
      data: { companies }
    });
  }

  setReconnectAttempts(attempts) {
    this.state.reconnectAttempts = attempts;
    this.notifyListeners('reconnectAttempts', attempts);
    this.channel.postMessage({
      type: 'RECONNECT_ATTEMPTS',
      data: { attempts }
    });
  }

  // Получение текущего состояния
  getState() {
    return { ...this.state };
  }

  // Получение конкретного значения
  getValue(key) {
    return this.state[key];
  }

  // Закрытие канала
  close() {
    this.channel.close();
    this.listeners.clear();
  }
}

// Создаем глобальный экземпляр
const stateManager = new StateManager();

export default stateManager;
