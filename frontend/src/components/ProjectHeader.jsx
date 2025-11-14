export default function ProjectHeader({
  title,
  subtitle,
  status,
  onBack,
  meta,
}) {
  return (
    <header className="w-full flex flex-col gap-3 md:flex-row md:items-center md:justify-between bg-slate-900/70 border border-white/5 rounded-2xl px-6 py-4 shadow-xl text-slate-100">
      <div className="space-y-1">
        <div className="flex items-center gap-3">
          {onBack ? (
            <button
              type="button"
              onClick={onBack}
              className="inline-flex items-center gap-2 rounded-xl bg-slate-800/70 hover:bg-slate-700/70 transition-colors px-3 py-1.5 text-sm font-medium text-slate-200 border border-white/10"
            >
              ← Назад
            </button>
          ) : null}
          <h1 className="text-2xl font-bold tracking-wide">
            {title ?? "Проект"}
          </h1>
        </div>
        {subtitle ? (
          <p className="text-sm text-slate-300 max-w-3xl">{subtitle}</p>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-3 text-sm items-center">
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
