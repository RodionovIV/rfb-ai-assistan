/*
  React single-file component: AI Assistant UI
  - Uses TailwindCSS for styling (ensure Tailwind is set up in your project)
  - Uses axios for HTTP requests (npm install axios)

  How to use:
  1. Put this file in your React app (e.g. src/components/AIAssistant.jsx)
  2. Ensure Tailwind is configured and imported in your project (index.css)
  3. npm install axios
  4. Import and render <AIAssistant /> in your App

  Notes about backend integration (matches your spec):
  - On page load the component fetches session titles from GET /api/v1/topics
  - Creating a new session only creates a client-side, untitled session; the backend will form the title on the first call to POST /api/v1/dialog
  - When sending a message we POST to /api/v1/dialog with { session_id, text }
  - If the dialog response contains a `title` field, the UI updates that session's title
*/

import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import { API_PREFIX } from "../config/api";

export default function AIAssistant() {
  const [sessions, setSessions] = useState([]); // { id, title (nullable), lastUpdated }
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messagesMap, setMessagesMap] = useState({}); // sessionId -> [{sender, text, ts}]
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [typingDots, setTypingDots] = useState("");
  const dotsInterval = useRef(null);
  const messagesEndRef = useRef(null);

  // Fetch session titles only on first load
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await axios.get(`${API_PREFIX}/topics`);
        if (!mounted) return;
        // Expecting array of { id, title }
        const topics = Array.isArray(res.data) ? res.data : [];
        setSessions(
          topics.map((t) => ({ id: t.id ?? t.topic_id ?? t._id ?? t.name ?? JSON.stringify(t), title: t.title ?? t.name ?? "Untitled" }))
        );
        if (topics.length > 0) setActiveSessionId(topics[0].id ?? topics[0].topic_id ?? topics[0]._id);
      } catch (e) {
        console.error("Failed to load topics:", e);
        // start with an initial session if backend unreachable
        const tmpId = `s-${Date.now()}`;
        setSessions([{ id: tmpId, title: null }]);
        setActiveSessionId(tmpId);
      }
    })();

    return () => { mounted = false; };
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messagesMap, loading]);

  // Typing dots animation while loading
  useEffect(() => {
    if (loading) {
      let n = 0;
      setTypingDots("");
      dotsInterval.current = setInterval(() => {
        n = (n + 1) % 4; // 0..3
        setTypingDots(".".repeat(n));
      }, 450);
    } else {
      clearInterval(dotsInterval.current);
      setTypingDots("");
    }
    return () => clearInterval(dotsInterval.current);
  }, [loading]);

  const createNewSession = () => {
    const id = `new-${Date.now()}`;
    setSessions((s) => [{ id, title: null, lastUpdated: Date.now() }, ...s]);
    setActiveSessionId(id);
    setMessagesMap((m) => ({ ...m, [id]: [] }));
  };

  const addMessage = (sessionId, sender, text) => {
    setMessagesMap((m) => {
      const prev = m[sessionId] ?? [];
      return { ...m, [sessionId]: [...prev, { sender, text, ts: Date.now() }] };
    });
  };

  const sendMessage = async () => {
    if (!input.trim() || !activeSessionId || loading) return;
    const text = input.trim();

    // Add user message locally
    addMessage(activeSessionId, "user", text);
    setInput("");
    setLoading(true);

    try {
      // Send to backend. Payload shape you can adapt.
      const payload = { conversationId: activeSessionId, content: text };
      console.log("Payload перед отправкой:", payload);
      const res = await axios.post(`${API_PREFIX}/dialog`, payload);

      // Expected response: { reply: '...', title?: 'Topic title' }
      const reply = (res.data && (res.data.reply ?? res.data.text ?? res.data.response)) || "(пустой ответ)";
      addMessage(activeSessionId, "bot", reply);

      // If backend provided a title on first dialog, update sessions list
      if (res.data && res.data.title) {
        setSessions((s) => s.map((sess) => sess.id === activeSessionId ? { ...sess, title: res.data.title } : sess));
      }

      // Optionally update lastUpdated
      setSessions((s) => s.map((sess) => sess.id === activeSessionId ? { ...sess, lastUpdated: Date.now() } : sess));
    } catch (err) {
      console.error("Dialog error:", err);
      addMessage(activeSessionId, "bot", "Ошибка: не удалось получить ответ от сервера.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const activeMessages = messagesMap[activeSessionId] ?? [];

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-700 text-white">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-6 border-b border-white/10">
        <h1 className="text-3xl font-bold tracking-wider">AI - assistant</h1>
        <div className="text-right">
          <div className="text-sm opacity-90">Добро пожаловать,</div>
          <div className="font-semibold">UserName</div>
        </div>
      </header>

      <main className="flex-1 flex overflow-hidden p-6 gap-6">
        {/* Left: spacer or could hold additional tools */}
        <div className="w-0 md:w-1/12" />

        {/* Center: Chat window */}
        <section className="flex-1 max-w-3xl flex flex-col bg-white/6 rounded-2xl p-4 shadow-lg">
          <div className="flex items-center justify-between mb-3 px-2">
            <div className="font-medium">Сессия: {sessions.find(s => s.id === activeSessionId)?.title ?? "(без названия)"}</div>
            <div className="text-sm opacity-80">ID: {activeSessionId ?? "-"}</div>
          </div>

          <div className="flex-1 overflow-y-auto rounded-lg p-4 space-y-3 bg-white/5" style={{ minHeight: 320 }}>
            {activeMessages.length === 0 && !loading ? (
              <div className="text-center opacity-80">Начните диалог — напишите сообщение внизу</div>
            ) : (
              activeMessages.map((m, i) => (
                <div key={i} className={`max-w-[80%] p-3 rounded-lg ${m.sender === 'user' ? 'ml-auto bg-blue-500/90 text-white' : 'mr-auto bg-white/10 text-white'}`}>
                  <div className="whitespace-pre-wrap">{m.text}</div>
                </div>
              ))
            )}

            {loading && (
              <div className="mr-auto bg-white/10 rounded-lg p-3 inline-block">
                <span className="italic">Ассистент печатает сообщение{typingDots}</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="mt-4 pt-3 border-t border-white/10">
            <div className="flex gap-3 items-end">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Введите сообщение... (Enter — отправить, Shift+Enter — новая строка)"
                className="flex-1 min-h-[48px] max-h-40 resize-none rounded-lg p-3 bg-white text-black placeholder-black/50 focus:outline-none focus:ring-2 focus:ring-white/20"
              />

              <button
                onClick={sendMessage}
                disabled={loading}
                className="px-4 py-2 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 text-white font-semibold disabled:opacity-60"
              >
                Отправить
              </button>
            </div>
          </div>
        </section>

        {/* Right: Sessions */}
        <aside className="w-80 flex-shrink-0 bg-white/6 rounded-2xl p-4 shadow-lg flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Сессии</h2>
            <button
              onClick={createNewSession}
              className="text-sm px-3 py-1 rounded-md bg-white/10"
            >
              Новая сессия
            </button>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2">
            {sessions.length === 0 ? (
              <div className="text-sm opacity-80">Сессий нет</div>
            ) : (
              sessions.map((s) => (
                <div
                  key={s.id}
                  onClick={() => setActiveSessionId(s.id)}
                  className={`p-3 rounded-md cursor-pointer hover:bg-white/8 ${s.id === activeSessionId ? 'ring-2 ring-white/20 bg-white/10' : ''}`}
                >
                  <div className="font-medium truncate">{s.title ?? '(без названия)'}</div>
                  <div className="text-xs opacity-70 truncate">ID: {s.id}</div>
                </div>
              ))
            )}
          </div>

          <div className="mt-3 text-xs opacity-70">Заголовки загружаются при открытии страницы. Новая сессия получает имя после первого запроса к /api/v1/dialog.</div>
        </aside>
      </main>

      <footer className="text-center py-4 text-sm opacity-80">Версия прототипа</footer>
    </div>
  );
}
