"""
Gradio приложение для AI Assistant
Заменяет FastAPI backend и React frontend
Точное воспроизведение визуала оригинального React приложения
"""
import gradio as gr
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import time
import json


class SessionManager:
    """Менеджер для управления сессиями диалогов"""
    
    def __init__(self):
        # Хранилище сессий: session_id -> {title, messages, created_at, updated_at}
        self.sessions: Dict[str, Dict] = {}
        self.current_session_id: Optional[str] = None
    
    def create_session(self) -> str:
        """Создает новую сессию и возвращает её ID"""
        session_id = f"new-{int(time.time() * 1000)}"
        self.sessions[session_id] = {
            "title": None,
            "messages": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        self.current_session_id = session_id
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Получает данные сессии по ID"""
        return self.sessions.get(session_id)
    
    def get_all_sessions(self) -> List[Dict]:
        """Возвращает список всех сессий"""
        sessions_list = []
        for session_id, session_data in self.sessions.items():
            sessions_list.append({
                "id": session_id,
                "title": session_data["title"],
                "updated_at": session_data["updated_at"]
            })
        # Сортируем по дате обновления (новые сверху)
        sessions_list.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions_list
    
    def add_message(self, session_id: str, sender: str, text: str):
        """Добавляет сообщение в сессию"""
        if session_id not in self.sessions:
            return
        
        self.sessions[session_id]["messages"].append({
            "sender": sender,
            "text": text,
            "ts": int(time.time() * 1000)
        })
        self.sessions[session_id]["updated_at"] = datetime.now()
    
    def set_title(self, session_id: str, title: str):
        """Устанавливает название сессии"""
        if session_id in self.sessions:
            self.sessions[session_id]["title"] = title


# Глобальный менеджер сессий
session_manager = SessionManager()


# Кастомный CSS для точного воспроизведения визуала
CUSTOM_CSS = """
/* Основной фон - градиент от синего через индиго к фиолетовому */
.gradio-container {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
    background: linear-gradient(to bottom right, #2563eb, #4f46e5, #7c3aed) !important;
    min-height: 100vh !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* Обертка всего контента */
#component-0 {
    background: transparent !important;
    padding: 0 !important;
}

/* Убираем стандартные стили Gradio */
.container {
    max-width: 100% !important;
    padding: 0 !important;
}

/* Header */
.header-wrapper {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    background: transparent;
    color: white;
}

.header-title {
    font-size: 30px;
    font-weight: bold;
    letter-spacing: 0.05em;
    color: white;
    margin: 0;
}

.header-welcome {
    text-align: right;
    color: white;
}

.header-welcome .text-sm {
    font-size: 14px;
    opacity: 0.9;
}

.header-welcome .username {
    font-weight: 600;
}

/* Main container */
.main-wrapper {
    display: flex;
    flex: 1;
    overflow: hidden;
    padding: 24px;
    gap: 24px;
    min-height: calc(100vh - 200px);
}

/* Левая пустая область */
.left-spacer {
    width: 0;
}

@media (min-width: 768px) {
    .left-spacer {
        width: 8.33%;
    }
}

/* Центральная панель чата */
.chat-section {
    flex: 1;
    max-width: 768px;
    display: flex;
    flex-direction: column;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

.chat-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    padding: 0 8px;
    color: white;
}

.chat-header .session-title {
    font-weight: 500;
    font-size: 16px;
}

.chat-header .session-id {
    font-size: 14px;
    opacity: 0.8;
}

/* Область сообщений */
.messages-container {
    flex: 1;
    overflow-y: auto;
    border-radius: 8px;
    padding: 16px;
    background: rgba(255, 255, 255, 0.05);
    min-height: 320px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 16px;
}

.message {
    max-width: 80%;
    display: flex;
}

.message.user-message {
    margin-left: auto;
    justify-content: flex-end;
}

.message.bot-message {
    margin-right: auto;
    justify-content: flex-start;
}

.message-content {
    padding: 12px;
    border-radius: 8px;
    white-space: pre-wrap;
    word-wrap: break-word;
}

.user-content {
    background: rgba(59, 130, 246, 0.9);
    color: white;
}

.bot-content {
    background: rgba(255, 255, 255, 0.1);
    color: white;
}

.empty-messages {
    text-align: center;
    opacity: 0.8;
    color: white;
}

.typing-indicator {
    margin-right: auto;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 12px;
    display: inline-block;
    color: white;
    font-style: italic;
}

.typing-dots {
    display: inline-block;
    min-width: 1em;
}

/* Input area */
.input-section {
    margin-top: 16px;
    padding-top: 12px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.input-wrapper {
    display: flex;
    gap: 12px;
    align-items: flex-end;
}

/* Textarea - скрываем label */
textarea {
    flex: 1;
    min-height: 48px !important;
    max-height: 160px !important;
    resize: none !important;
    border-radius: 8px !important;
    padding: 12px !important;
    background: white !important;
    color: black !important;
    border: none !important;
}

textarea:disabled {
    background: white !important;
    color: black !important;
    opacity: 1 !important;
}

textarea::placeholder {
    color: rgba(0, 0, 0, 0.5) !important;
}

textarea:focus {
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.2) !important;
}

textarea[disabled] {
    background: white !important;
    opacity: 1 !important;
    cursor: text !important;
}

/* Кнопка отправки */
button.primary {
    padding: 8px 16px !important;
    border-radius: 8px !important;
    background: linear-gradient(to bottom right, #3b82f6, #4f46e5) !important;
    color: white !important;
    font-weight: 600 !important;
    border: none !important;
    cursor: pointer !important;
    transition: opacity 0.2s !important;
}

button.primary:hover {
    opacity: 0.9 !important;
}

button.primary:disabled {
    opacity: 0.6 !important;
    cursor: not-allowed !important;
}

/* Боковая панель сессий */
.sessions-sidebar {
    width: 320px;
    flex-shrink: 0;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    display: flex;
    flex-direction: column;
}

.sessions-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
}

.sessions-title {
    font-weight: 600;
    color: white;
    font-size: 16px;
    margin: 0;
}

.new-session-btn {
    font-size: 14px !important;
    padding: 4px 12px !important;
    border-radius: 6px !important;
    background: rgba(255, 255, 255, 0.1) !important;
    color: white !important;
    border: none !important;
    cursor: pointer !important;
    transition: background 0.2s !important;
}

.new-session-btn:hover {
    background: rgba(255, 255, 255, 0.15) !important;
}

.sessions-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 12px;
}

.session-item {
    padding: 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.2s;
    color: white;
    border: none !important;
    background: transparent !important;
}

.session-item:hover {
    background: rgba(255, 255, 255, 0.08) !important;
}

.session-item.active {
    background: rgba(255, 255, 255, 0.1) !important;
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.2) !important;
}

.session-title {
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-bottom: 4px;
    color: white;
}

.session-id {
    font-size: 12px;
    opacity: 0.7;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: white;
}

.empty-sessions {
    font-size: 14px;
    opacity: 0.8;
    color: white;
}

.sessions-info {
    margin-top: 12px;
    font-size: 12px;
    opacity: 0.7;
    color: white;
}

/* Footer */
.footer {
    text-align: center;
    padding: 16px;
    font-size: 14px;
    opacity: 0.8;
    color: white;
}

/* Скрываем стандартные элементы Gradio */
.panel {
    background: transparent !important;
    border: none !important;
}

footer {
    display: none !important;
}

/* Radio для сессий - скрываем стандартный вид */
.radio-group {
    display: none !important;
}

/* Скрываем label у textarea */
label {
    display: none !important;
}
"""


def process_message(message: str, session_id: str):
    """Обрабатывает сообщение пользователя и возвращает ответ"""
    # Сообщение пользователя уже добавлено в submit_with_typing
    # Получаем ответ от AI (пока заглушка, как в оригинальном коде)
    response = "Ok"
    
    # Добавляем ответ ассистента в сессию
    session_manager.add_message(session_id, "assistant", response)
    
    # Если это первое сообщение в сессии, генерируем название
    session = session_manager.get_session(session_id)
    if session and session["title"] is None and len(session["messages"]) >= 2:
        title = message.strip()[:50] + "..." if len(message.strip()) > 50 else message.strip()
        session_manager.set_title(session_id, title)
    
    return response


def get_messages_html(session_id: str, show_typing: bool = False) -> str:
    """Возвращает HTML для отображения сообщений"""
    if not session_id or session_id not in session_manager.sessions:
        return '<div class="empty-messages">Начните диалог — напишите сообщение внизу</div>'
    
    session = session_manager.sessions[session_id]
    messages = session["messages"]
    
    html_parts = []
    
    if not messages:
        if not show_typing:
            return '<div class="empty-messages">Начните диалог — напишите сообщение внизу</div>'
    else:
        for msg in messages:
            if msg["sender"] == "user":
                text = msg["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;")
                html_parts.append(f'''
                <div class="message user-message">
                    <div class="message-content user-content">{text}</div>
                </div>
                ''')
            elif msg["sender"] == "assistant":
                text = msg["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;")
                html_parts.append(f'''
                <div class="message bot-message">
                    <div class="message-content bot-content">{text}</div>
                </div>
                ''')
    
    # Добавляем индикатор типинга если нужно
    if show_typing:
        html_parts.append('''
        <div class="message bot-message">
            <div class="message-content bot-content typing-indicator" id="typing-indicator">
                <span class="typing-text">Ассистент печатает сообщение</span><span class="typing-dots"></span>
            </div>
        </div>
        ''')
    
    return ''.join(html_parts)


def get_sessions_display_data(active_session_id: str) -> Tuple[List[Tuple[str, str]], str]:
    """Возвращает данные для отображения сессий в Radio"""
    sessions = session_manager.get_all_sessions()
    
    if not sessions:
        return [], None
    
    choices = []
    for session in sessions:
        title = session["title"] or "(без названия)"
        session_id_short = session["id"][:20] + "..." if len(session["id"]) > 20 else session["id"]
        label = f"{title} (ID: {session_id_short})"
        choices.append((label, session["id"]))
    
    # Возвращаем выбранную сессию или первую
    selected = active_session_id if active_session_id and any(s[1] == active_session_id for s in choices) else (choices[0][1] if choices else None)
    
    return choices, selected


def get_session_title(session_id: str) -> str:
    """Возвращает название сессии"""
    if not session_id:
        return "(без названия)"
    session = session_manager.get_session(session_id)
    if session:
        return session["title"] or "(без названия)"
    return "(без названия)"


def get_session_id_short(session_id: str) -> str:
    """Возвращает короткий ID сессии"""
    if not session_id:
        return "-"
    return session_id[:20] + "..." if len(session_id) > 20 else session_id


# Создаем интерфейс Gradio
with gr.Blocks(
    title="AI Assistant",
    css=CUSTOM_CSS,
    theme=gr.themes.Base()
) as app:
    
    # Скрытая переменная для хранения текущего session_id
    current_session = gr.State(value=None)
    
    # Основная структура
    with gr.Column(elem_id="main-container"):
        # Header
        with gr.Row(elem_classes=["header-wrapper"]):
            gr.HTML('<h1 class="header-title">AI - assistant</h1>')
            gr.HTML('''
            <div class="header-welcome">
                <div class="text-sm">Добро пожаловать,</div>
                <div class="username">UserName</div>
            </div>
            ''')
        
        # Main content
        with gr.Row(elem_classes=["main-wrapper"]):
            # Левая пустая область
            gr.HTML('<div class="left-spacer"></div>')
            
            # Центральная панель чата
            with gr.Column(elem_classes=["chat-section"]):
                # Заголовок сессии
                with gr.Row(elem_classes=["chat-header"]):
                    session_title_display = gr.HTML(
                        '<div class="session-title">Сессия: <span id="session-title-text">(без названия)</span></div>'
                    )
                    session_id_display = gr.HTML(
                        '<div class="session-id">ID: <span id="session-id-text">-</span></div>'
                    )
                
                # Область сообщений - используем HTML компонент
                messages_html = gr.HTML(
                    value='<div class="messages-container"><div class="empty-messages">Начните диалог — напишите сообщение внизу</div></div>',
                    elem_classes=["messages-container"]
                )
                
                # Input area
                with gr.Column(elem_classes=["input-section"]):
                    with gr.Row(elem_classes=["input-wrapper"]):
                        msg = gr.Textbox(
                            label="",
                            placeholder="Введите сообщение... (Enter — отправить, Shift+Enter — новая строка)",
                            lines=2,
                            scale=4,
                            container=False,
                            interactive=True  # Явно указываем что интерактивное
                        )
                        submit_btn = gr.Button("Отправить", elem_classes=["primary"], scale=1)
            
            # Боковая панель сессий
            with gr.Column(elem_classes=["sessions-sidebar"]):
                with gr.Row(elem_classes=["sessions-header"]):
                    gr.HTML('<h2 class="sessions-title">Сессии</h2>')
                    new_session_btn = gr.Button("Новая сессия", elem_classes=["new-session-btn"], scale=1)
                
                # HTML для отображения списка сессий
                sessions_list_html = gr.HTML(
                    value='<div class="sessions-list"><div class="empty-sessions">Сессий нет</div></div>',
                    elem_classes=["sessions-list"]
                )
                
                # Скрытый Radio компонент для переключения сессий (управляется через JavaScript)
                session_radio = gr.Radio(
                    choices=[],
                    label="",
                    visible=False,
                    interactive=True,
                    elem_id="session-radio-selector"
                )
                
                gr.HTML('''
                <div class="sessions-info">
                    Заголовки загружаются при открытии страницы. Новая сессия получает имя после первого запроса к /api/v1/dialog.
                </div>
                ''')
        
        # Footer
        gr.HTML('<div class="footer">Версия прототипа</div>')
        
        # JavaScript для обработки кликов на сессиях - добавляем в конце
        gr.HTML(
            value="""
            <script>
            window.switchToSession = function(sessionId) {
                console.log('Switching to session:', sessionId);
                const radio = document.querySelector('#session-radio-selector input[value="' + sessionId + '"]');
                if (radio) {
                    radio.checked = true;
                    radio.dispatchEvent(new Event('change', { bubbles: true }));
                    radio.dispatchEvent(new Event('input', { bubbles: true }));
                } else {
                    console.error('Radio option not found for session:', sessionId);
                    // Пробуем найти через data-атрибуты
                    const sessionItem = document.querySelector('[data-session-id="' + sessionId + '"]');
                    if (sessionItem) {
                        // Пробуем найти radio через родительские элементы
                        const container = document.querySelector('#session-radio-selector');
                        if (container) {
                            const allRadios = container.querySelectorAll('input[type="radio"]');
                            for (let r of allRadios) {
                                if (r.value === sessionId) {
                                    r.checked = true;
                                    r.dispatchEvent(new Event('change', { bubbles: true }));
                                    break;
                                }
                            }
                        }
                    }
                }
            };
            
            // Автопрокрутка
            function scrollMessages() {
                const container = document.querySelector('.messages-container');
                if (container) {
                    container.scrollTop = container.scrollHeight;
                }
            }
            setInterval(scrollMessages, 100);
            </script>
            """,
            visible=False
        )
    
    # Обработчики событий
    def get_sessions_html(session_id: str) -> str:
        """Генерирует HTML для списка сессий с кнопками для каждой сессии"""
        sessions = session_manager.get_all_sessions()
        
        if not sessions:
            return '<div class="sessions-list"><div class="empty-sessions">Сессий нет</div></div>'
        
        html_parts = []
        for session in sessions:
            sid = session["id"]
            title = session["title"] or "(без названия)"
            is_active = "active" if sid == session_id else ""
            session_id_short = sid[:20] + "..." if len(sid) > 20 else sid
            
            # Экранируем HTML
            title_escaped = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            # Используем data-атрибуты для хранения session_id
            html_parts.append(f'''
            <div class="session-item {is_active}" data-session-id="{sid}" onclick="window.switchToSession('{sid}')" style="cursor: pointer;">
                <div class="session-title">{title_escaped}</div>
                <div class="session-id">ID: {session_id_short}</div>
            </div>
            ''')
        
        return f'<div class="sessions-list">{chr(10).join(html_parts)}</div>'
    
    def handle_submit(message, session_id, show_typing_step: bool = False):
        """Обработчик отправки сообщения"""
        if not message or not message.strip():
            return gr.update(), messages_html.value, session_id, session_title_display.value, session_id_display.value, sessions_list_html.value, gr.update(interactive=True)
        
        if not session_id:
            session_id = session_manager.create_session()
        
        # Добавляем сообщение пользователя сразу
        user_message = message.strip()
        session_manager.add_message(session_id, "user", user_message)
        
        # Если это первый шаг, показываем индикатор типинга
        if not show_typing_step:
            messages_html_content = get_messages_html(session_id, show_typing=True)
            messages_html_value = f'<div class="messages-container">{messages_html_content}</div>'
            typing_js = """
            <script>
            (function() {
                let n = 0;
                const dotsEl = document.querySelector('.typing-dots');
                if (dotsEl) {
                    const interval = setInterval(() => {
                        n = (n + 1) % 4;
                        dotsEl.textContent = '.'.repeat(n);
                    }, 450);
                    
                    // Остановим через 2 секунды и вызовем обработку ответа
                    setTimeout(() => {
                        clearInterval(interval);
                        // Вызываем обработку ответа
                        if (window.processResponse) {
                            window.processResponse();
                        }
                    }, 2000);
                }
            })();
            </script>
            """
            messages_html_value += typing_js
            
            scroll_js = "<script>setTimeout(() => { const c = document.querySelector('.messages-container'); if (c) c.scrollTop = c.scrollHeight; }, 100);</script>"
            messages_html_value += scroll_js
            
            return (
                gr.update(value=""), 
                messages_html_value, 
                session_id, 
                session_title_display.value, 
                session_id_display.value, 
                sessions_list_html.value,
                gr.update(interactive=False)  # Блокируем кнопку
            )
        
        # Второй шаг - обрабатываем ответ
        import time
        time.sleep(0.5)  # Небольшая задержка для реалистичности
        
        response = process_message(user_message, session_id)
        
        # Обновляем HTML сообщений (без индикатора типинга)
        messages_html_content = get_messages_html(session_id, show_typing=False)
        messages_html_value = f'<div class="messages-container">{messages_html_content}</div>'
        
        # Обновляем информацию о сессии
        title = get_session_title(session_id)
        session_title_value = f'<div class="session-title">Сессия: <span id="session-title-text">{title}</span></div>'
        session_id_value = f'<div class="session-id">ID: <span id="session-id-text">{get_session_id_short(session_id)}</span></div>'
        
        # Обновляем список сессий
        sessions_html_value = get_sessions_html(session_id)
        
        # Прокрутка вниз
        scroll_js = "<script>setTimeout(() => { const c = document.querySelector('.messages-container'); if (c) c.scrollTop = c.scrollHeight; }, 100);</script>"
        messages_html_value += scroll_js
        
        return (
            gr.update(value=""), 
            messages_html_value, 
            session_id, 
            session_title_value, 
            session_id_value, 
            sessions_html_value,
            gr.update(interactive=True)  # Разблокируем кнопку
        )
    
    def handle_submit_step1(message, session_id):
        """Первый шаг - показываем индикатор типинга"""
        return handle_submit(message, session_id, show_typing_step=False)
    
    def handle_submit_step2(message, session_id):
        """Второй шаг - обрабатываем ответ"""
        return handle_submit(message, session_id, show_typing_step=True)
    
    def handle_new_session():
        """Создание новой сессии"""
        session_id = session_manager.create_session()
        messages_html_value = '<div class="messages-container"><div class="empty-messages">Начните диалог — напишите сообщение внизу</div></div>'
        sessions_html_value = get_sessions_html(session_id)
        session_title_value = '<div class="session-title">Сессия: <span id="session-title-text">(без названия)</span></div>'
        session_id_value = f'<div class="session-id">ID: <span id="session-id-text">{get_session_id_short(session_id)}</span></div>'
        
        # Обновляем Radio
        choices = get_session_radio_choices()
        
        return (
            session_id,  # current_session
            messages_html_value,  # messages_html
            sessions_html_value,  # sessions_list_html
            session_title_value,  # session_title_display
            session_id_value,  # session_id_display
            gr.update(choices=choices, value=session_id)  # session_radio
        )
    
    def handle_session_change(selected_session_id):
        """Переключение сессии"""
        if not selected_session_id:
            choices = get_session_radio_choices()
            return (
                None,  # current_session
                messages_html.value,  # messages_html
                sessions_list_html.value,  # sessions_list_html
                session_title_display.value,  # session_title_display
                session_id_display.value,  # session_id_display
                gr.update(choices=choices)  # session_radio
            )
        
        session_manager.current_session_id = selected_session_id
        
        messages_html_content = get_messages_html(selected_session_id, show_typing=False)
        messages_html_value = f'<div class="messages-container">{messages_html_content}</div>'
        
        title = get_session_title(selected_session_id)
        session_title_value = f'<div class="session-title">Сессия: <span id="session-title-text">{title}</span></div>'
        session_id_value = f'<div class="session-id">ID: <span id="session-id-text">{get_session_id_short(selected_session_id)}</span></div>'
        
        sessions_html_value = get_sessions_html(selected_session_id)
        
        # Обновляем Radio choices
        choices = get_session_radio_choices()
        selected_label = None
        for label, sid in choices:
            if sid == selected_session_id:
                selected_label = label
                break
        
        return (
            selected_session_id,  # current_session
            messages_html_value,  # messages_html
            sessions_html_value,  # sessions_list_html
            session_title_value,  # session_title_display
            session_id_value,  # session_id_display
            gr.update(choices=choices, value=selected_session_id if selected_label else None)  # session_radio
        )
    
    # Привязка событий
    def submit_with_typing(message, session_id):
        """Обработчик отправки с показом индикатора типинга"""
        if not message or not message.strip():
            return (
                gr.update(), 
                messages_html.value, 
                session_id, 
                session_title_display.value, 
                session_id_display.value, 
                sessions_list_html.value,
                gr.update(interactive=True),
                ""  # last_message_for_processing
            )
        
        if not session_id:
            session_id = session_manager.create_session()
        
        # Добавляем сообщение пользователя
        user_message = message.strip()
        session_manager.add_message(session_id, "user", user_message)
        
        # Показываем индикатор типинга
        messages_html_content = get_messages_html(session_id, show_typing=True)
        messages_html_value = f'<div class="messages-container">{messages_html_content}</div>'
        
        # JavaScript для анимации точек
        typing_js = """
        <script>
        (function() {
            let n = 0;
            const dotsEl = document.querySelector('.typing-dots');
            if (dotsEl) {
                const interval = setInterval(() => {
                    n = (n + 1) % 4;
                    dotsEl.textContent = '.'.repeat(n);
                }, 450);
                
                // Остановим когда появится новый контент (в process_response)
                window.currentTypingInterval = interval;
            }
        })();
        </script>
        """
        messages_html_value += typing_js
        
        scroll_js = "<script>setTimeout(() => { const c = document.querySelector('.messages-container'); if (c) c.scrollTop = c.scrollHeight; }, 100);</script>"
        messages_html_value += scroll_js
        
        # Обновляем Radio при отправке сообщения
        choices = get_session_radio_choices()
        
        return (
            gr.update(value="", interactive=True),  # msg - очищаем поле ввода, но оставляем активным
            messages_html_value,  # messages_html
            session_id,  # current_session
            session_title_display.value,  # session_title_display
            session_id_display.value,  # session_id_display
            sessions_list_html.value,  # sessions_list_html
            gr.update(interactive=False),  # submit_btn - блокируем
            user_message,  # last_message_for_processing - сохраняем сообщение для следующего шага
            gr.update(choices=choices, value=session_id)  # session_radio - обновляем
        )
    
    def process_response(saved_message, session_id):
        """Обрабатывает ответ после показа индикатора типинга"""
        import time
        time.sleep(1.2)  # Небольшая задержка для реалистичности
        
        if not saved_message:
            saved_message = ""
        
        response = process_message(saved_message.strip(), session_id)
        
        # Обновляем HTML сообщений (без индикатора типинга)
        messages_html_content = get_messages_html(session_id, show_typing=False)
        messages_html_value = f'<div class="messages-container">{messages_html_content}</div>'
        
        # Останавливаем анимацию точек
        stop_typing_js = """
        <script>
        if (window.currentTypingInterval) {
            clearInterval(window.currentTypingInterval);
            window.currentTypingInterval = null;
        }
        </script>
        """
        messages_html_value += stop_typing_js
        
        # Обновляем информацию о сессии
        title = get_session_title(session_id)
        session_title_value = f'<div class="session-title">Сессия: <span id="session-title-text">{title}</span></div>'
        session_id_value = f'<div class="session-id">ID: <span id="session-id-text">{get_session_id_short(session_id)}</span></div>'
        
        # Обновляем список сессий
        sessions_html_value = get_sessions_html(session_id)
        
        scroll_js = "<script>setTimeout(() => { const c = document.querySelector('.messages-container'); if (c) c.scrollTop = c.scrollHeight; }, 100);</script>"
        messages_html_value += scroll_js
        
        # Обновляем Radio после обработки ответа
        choices = get_session_radio_choices()
        
        return (
            gr.update(interactive=True),  # msg - разблокируем поле ввода
            messages_html_value, 
            session_id, 
            session_title_value, 
            session_id_value, 
            sessions_html_value,
            gr.update(interactive=True),  # submit_btn - разблокируем кнопку
            gr.update(choices=choices, value=session_id)  # session_radio - обновляем
        )
    
    # Скрытое состояние для хранения последнего сообщения для обработки
    last_message_for_processing = gr.State(value="")
    
    msg.submit(
        submit_with_typing,
        inputs=[msg, current_session],
        outputs=[msg, messages_html, current_session, session_title_display, session_id_display, sessions_list_html, submit_btn, last_message_for_processing, session_radio]
    ).then(
        process_response,
        inputs=[last_message_for_processing, current_session],
        outputs=[msg, messages_html, current_session, session_title_display, session_id_display, sessions_list_html, submit_btn, session_radio]
    )
    
    submit_btn.click(
        submit_with_typing,
        inputs=[msg, current_session],
        outputs=[msg, messages_html, current_session, session_title_display, session_id_display, sessions_list_html, submit_btn, last_message_for_processing, session_radio]
    ).then(
        process_response,
        inputs=[last_message_for_processing, current_session],
        outputs=[msg, messages_html, current_session, session_title_display, session_id_display, sessions_list_html, submit_btn, session_radio]
    )
    
    new_session_btn.click(
        handle_new_session,
        outputs=[current_session, messages_html, sessions_list_html, session_title_display, session_id_display, session_radio]
    )
    
    # Обработчик переключения сессии через кнопку
    def switch_session_via_btn():
        """Переключает сессию используя глобальную переменную из JavaScript"""
        # Получаем session_id из JavaScript через задержку
        import time
        time.sleep(0.1)  # Небольшая задержка для установки значения
        
        # Пробуем получить значение из JavaScript через HTML
        # Но лучше использовать другой подход - передавать через состояние
        # Пока используем текущую активную сессию или создаем новую
        if session_manager.current_session_id:
            session_id = session_manager.current_session_id
        else:
            # Если нет активной, берем первую из списка
            sessions = session_manager.get_all_sessions()
            if sessions:
                session_id = sessions[0]["id"]
            else:
                session_id = session_manager.create_session()
        
        # Используем JavaScript для получения выбранной сессии
        # Временно используем последнюю активную или создаем новую
        return handle_session_change(session_id)
    
    # Используем Radio компонент для переключения сессий (более надежно)
    def get_session_radio_choices():
        """Возвращает список сессий для Radio компонента"""
        sessions = session_manager.get_all_sessions()
        if not sessions:
            return []
        
        choices = []
        for session in sessions:
            title = session["title"] or "(без названия)"
            session_id_short = session["id"][:20] + "..." if len(session["id"]) > 20 else session["id"]
            label = f"{title} ({session_id_short})"
            choices.append((label, session["id"]))
        return choices
    
    # Обработчик изменения Radio
    def session_radio_change(selected_value):
        """Обработчик изменения выбранной сессии через Radio"""
        if selected_value:
            return handle_session_change(selected_value)
        # Если нет значения, возвращаем текущие значения + обновление Radio
        choices = get_session_radio_choices()
        return (
            current_session.value if current_session.value else None,  # current_session
            messages_html.value,  # messages_html
            sessions_list_html.value,  # sessions_list_html
            session_title_display.value,  # session_title_display
            session_id_display.value,  # session_id_display
            gr.update(choices=choices)  # session_radio
        )
    
    session_radio.change(
        session_radio_change,
        inputs=[session_radio],
        outputs=[current_session, messages_html, sessions_list_html, session_title_display, session_id_display, session_radio]
    )
    
    # Обновляем Radio при создании/изменении сессий
    def update_session_radio(session_id):
        """Обновляет Radio компонент с текущими сессиями"""
        choices = get_session_radio_choices()
        return gr.update(choices=choices, value=session_id if session_id else None)
    
    # При создании новой сессии обновляем Radio
    new_session_btn.click(
        lambda: update_session_radio(session_manager.current_session_id),
        outputs=[session_radio]
    )
    
    # Обновляем JavaScript для работы с Radio
    def update_switch_session_js():
        """Обновляет JavaScript функцию для переключения сессий"""
        choices = get_session_radio_choices()
        js_code = f"""
        <script>
        window.switchToSession = function(sessionId) {{
            console.log('Switching to session:', sessionId);
            const radio = document.querySelector('#session-radio-selector input[value="' + sessionId + '"]');
            if (radio) {{
                radio.checked = true;
                radio.dispatchEvent(new Event('change', {{ bubbles: true }}));
                radio.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }} else {{
                console.error('Radio option not found for session:', sessionId);
            }}
        }};
        </script>
        """
        return gr.HTML(js_code, visible=False)
    
    # Инициализация: создаем первую сессию при загрузке
    app.load(
        handle_new_session,
        outputs=[current_session, messages_html, sessions_list_html, session_title_display, session_id_display, session_radio]
    )


if __name__ == "__main__":
    # Запуск приложения
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        show_api=False
    )
