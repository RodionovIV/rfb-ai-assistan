import { useEffect, useRef, useState } from "react";

const normalizeMessage = (message) => ({
  role: message?.role ?? message?.sender ?? "assistant",
  content: message?.content ?? message?.text ?? "",
  createdAt: message?.created_at ?? message?.timestamp ?? message?.ts ?? null,
});

export default function ProjectChat({
  messages = [],
  onSend,
  isSending = false,
  error,
}) {
  const [draft, setDraft] = useState("");
  const [localError, setLocalError] = useState(null);
  const endRef = useRef(null);

  const normalizedMessages = messages.map(normalizeMessage);

  useEffect(() => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [normalizedMessages, isSending]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!draft.trim()) return;

    const message = draft.trim();
    setDraft("");
    setLocalError(null);

    try {
      await onSend?.(message);
    } catch (err) {
      setLocalError(err?.message ?? "Не удалось отправить сообщение");
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
    }
  };

  return (
    <section className="bg-slate-900/60 border border-white/5 rounded-2xl p-5 shadow-xl text-slate-100 flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Чат проекта</h2>
        {isSending ? (
          <span className="text-xs text-emerald-200 animate-pulse">Сохраняем контекст…</span>
        ) : null}
      </div>

      <div className="flex-1 min-h-[320px] max-h-[480px] overflow-y-auto space-y-3 pr-1">
        {!normalizedMessages.length ? (
          <div className="text-sm text-slate-300 bg-slate-800/60 rounded-xl px-4 py-3 border border-white/5 text-center">
            История сообщений отсутствует. Задайте вопрос, чтобы начать диалог с агентом.
          </div>
        ) : (
          normalizedMessages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap shadow border border-white/5 ${
                message.role === "user"
                  ? "ml-auto bg-indigo-500/80 text-white"
                  : message.role === "system"
                  ? "mx-auto bg-slate-800/70 text-slate-200"
                  : "mr-auto bg-slate-800/80 text-slate-100"
              }`}
            >
              {message.content}
            </div>
          ))
        )}
        {isSending ? (
          <div className="mr-auto bg-slate-800/70 text-slate-200 rounded-2xl px-4 py-2 text-sm border border-white/5">
            Агент формирует ответ…
          </div>
        ) : null}
        <div ref={endRef} />
      </div>

      {(error || localError) && (
        <div className="text-sm text-red-300 bg-red-900/30 border border-red-700/40 rounded-xl px-3 py-2">
          {error ?? localError}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <textarea
          className="w-full min-h-[120px] resize-y rounded-xl bg-slate-950/40 border border-white/10 text-slate-100 placeholder-slate-400 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          placeholder="Опишите, какие выводы вам нужны или задайте уточняющий вопрос"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isSending}
        />
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-slate-400">
            Нажмите Enter для отправки. Shift + Enter — новая строка.
          </span>
          <button
            type="submit"
            disabled={!draft.trim() || isSending}
            className={`px-5 py-2.5 rounded-xl font-semibold transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 ${
              !draft.trim() || isSending
                ? "bg-slate-700 text-slate-300 cursor-not-allowed"
                : "bg-indigo-500 hover:bg-indigo-400 text-white focus:ring-indigo-300"
            }`}
          >
            Отправить
          </button>
        </div>
      </form>
    </section>
  );
}
