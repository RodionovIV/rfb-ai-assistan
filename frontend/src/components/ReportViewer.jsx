export default function ReportViewer({ report, status = "idle", updatedAt, error }) {
  const formatDate = (value) => {
    if (!value) return null;
    try {
      const date = typeof value === "string" ? new Date(value) : value;
      if (Number.isNaN(date.getTime?.())) return null;
      return date.toLocaleString();
    } catch (err) {
      console.error("Failed to format date", err);
      return null;
    }
  };

  const renderBody = () => {
    if (status === "error") {
      return (
        <div className="text-red-200 bg-red-900/30 border border-red-700/50 rounded-xl p-4">
          {error ?? "Не удалось загрузить отчёт"}
        </div>
      );
    }

    if (status === "loading" || status === "uploading") {
      return (
        <div className="animate-pulse bg-slate-800/60 rounded-xl h-48" />
      );
    }

    if (status === "analyzing") {
      return (
        <div className="text-amber-200 bg-amber-900/20 border border-amber-600/30 rounded-xl p-4">
          Агент анализирует… Пожалуйста, подождите.
        </div>
      );
    }

    if (!report) {
      return (
        <div className="text-slate-300 bg-slate-800/60 border border-white/5 rounded-xl p-4 text-sm">
          Отчёт ещё не сформирован. Загрузите документ, чтобы запустить анализ.
        </div>
      );
    }

    return (
      <article className="prose prose-invert max-w-none">
        {Array.isArray(report) ? (
          report.map((section, index) => (
            <p key={index} className="whitespace-pre-wrap">
              {section}
            </p>
          ))
        ) : typeof report === "object" ? (
          <pre className="whitespace-pre-wrap text-sm bg-slate-900/80 p-4 rounded-xl border border-white/5 overflow-x-auto">
            {JSON.stringify(report, null, 2)}
          </pre>
        ) : (
          report
            .toString()
            .split(/\n{2,}/)
            .map((block, index) => (
              <p key={index} className="whitespace-pre-wrap">
                {block.trim()}
              </p>
            ))
        )}
      </article>
    );
  };

  return (
    <section className="bg-slate-900/60 border border-white/5 rounded-2xl p-5 shadow-xl text-slate-100 flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Отчёт</h2>
        {formatDate(updatedAt) ? (
          <span className="text-xs text-slate-300">Обновлено: {formatDate(updatedAt)}</span>
        ) : null}
      </div>
      <div className="flex-1 min-h-[240px] overflow-y-auto pr-1 space-y-4">
        {renderBody()}
      </div>
    </section>
  );
}
