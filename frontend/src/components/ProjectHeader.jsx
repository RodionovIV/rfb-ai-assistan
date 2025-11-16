import { useEffect, useState } from "react";

export default function ProjectHeader({
  title,
  subtitle,
  status,
  onBack,
  meta,
  onRename,
  isRenamingTitle = false,
  renameError = null,
  onDismissRenameError,
}) {
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [draftTitle, setDraftTitle] = useState(title ?? "");
  const canEditTitle = typeof onRename === "function";
  const resolvedTitle = title ?? "Проект";

  useEffect(() => {
    if (!isEditingTitle) {
      setDraftTitle(title ?? "");
    }
  }, [isEditingTitle, title]);

  const startEditing = () => {
    if (!canEditTitle) return;
    setIsEditingTitle(true);
    onDismissRenameError?.();
  };

  const cancelEditing = () => {
    setDraftTitle(title ?? "");
    setIsEditingTitle(false);
    onDismissRenameError?.();
  };

  const handleRenameSubmit = async (event) => {
    event.preventDefault();
    if (!canEditTitle) return;
    const nextTitle = draftTitle.trim();
    if (!nextTitle || nextTitle === resolvedTitle.trim()) {
      cancelEditing();
      return;
    }
    try {
      await onRename(nextTitle);
      setIsEditingTitle(false);
    } catch (err) {
      console.warn("Failed to rename project", err);
    }
  };

  return (
    <header className="w-full flex flex-col gap-3 md:flex-row md:items-center md:justify-between bg-slate-900/70 border border-white/5 rounded-2xl px-6 py-4 shadow-xl text-slate-100">
      <div className="space-y-2 max-w-3xl">
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center gap-3">
            {onBack ? (
              <button
                type="button"
                onClick={onBack}
                className="inline-flex items-center gap-2 rounded-xl bg-slate-800/70 hover:bg-slate-700/70 transition-colors px-3 py-1.5 text-sm font-medium text-slate-200 border border-white/10"
              >
                ← Назад
              </button>
            ) : null}
            {isEditingTitle ? (
              <form
                className="flex flex-wrap items-center gap-2"
                onSubmit={handleRenameSubmit}
              >
                <input
                  type="text"
                  value={draftTitle}
                  onChange={(event) => setDraftTitle(event.target.value)}
                  disabled={isRenamingTitle}
                  className="px-3 py-1.5 rounded-xl bg-slate-950/60 border border-white/15 text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-400 min-w-[220px]"
                  placeholder="Введите название проекта"
                />
                <button
                  type="submit"
                  disabled={isRenamingTitle || !draftTitle.trim()}
                  className={`px-3 py-1.5 rounded-xl text-sm font-semibold transition-colors ${
                    isRenamingTitle || !draftTitle.trim()
                      ? "bg-emerald-900/40 text-emerald-200 cursor-not-allowed"
                      : "bg-emerald-500 text-slate-900 hover:bg-emerald-400"
                  }`}
                >
                  {isRenamingTitle ? "Сохраняем..." : "Сохранить"}
                </button>
                <button
                  type="button"
                  onClick={cancelEditing}
                  className="px-3 py-1.5 rounded-xl text-sm font-semibold border border-white/15 text-slate-200 hover:bg-slate-800/70"
                >
                  Отмена
                </button>
              </form>
            ) : (
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-2xl font-bold tracking-wide">{resolvedTitle}</h1>
                {canEditTitle ? (
                  <button
                    type="button"
                    onClick={startEditing}
                    className="px-3 py-1.5 rounded-xl text-xs font-semibold border border-white/15 text-slate-200 hover:bg-slate-800/70"
                  >
                    Редактировать
                  </button>
                ) : null}
              </div>
            )}
          </div>
          {subtitle ? (
            <p className="text-sm text-slate-300 max-w-3xl">{subtitle}</p>
          ) : null}
          {isEditingTitle && renameError ? (
            <div className="text-sm text-red-200 bg-red-900/30 border border-red-700/40 rounded-xl px-3 py-2 flex items-center justify-between gap-3">
              <span>{renameError}</span>
              {onDismissRenameError ? (
                <button
                  type="button"
                  onClick={onDismissRenameError}
                  className="text-xs uppercase tracking-wide text-red-200/80 hover:text-red-100"
                >
                  Закрыть
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      <div className="flex flex-wrap gap-3 text-sm items-center justify-end">
        {status ? (
          <span className="inline-flex items-center gap-2 rounded-full bg-indigo-500/20 text-indigo-200 border border-indigo-400/30 px-4 py-1.5 uppercase tracking-wider">
            <span className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse" />
            {status}
          </span>
        ) : null}
        {meta?.map?.((item, index) => (
          <span
            key={index}
            className="inline-flex items-center gap-2 rounded-full bg-slate-800/80 text-slate-200 border border-white/10 px-4 py-1.5"
          >
            {item}
          </span>
        ))}
      </div>
    </header>
  );
}
