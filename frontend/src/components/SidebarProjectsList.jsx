import { Link } from "react-router-dom";

const normalizeProjectId = (project) =>
  project?.id ?? project?.project_id ?? project?.uuid ?? project?.slug ?? project?.name;

export default function SidebarProjectsList({
  projects,
  activeProjectId,
  onSelect,
  isLoading = false,
  error = null,
  emptyMessage = "Проекты отсутствуют",
}) {
  const handleSelect = (project) => {
    if (onSelect) {
      onSelect(project, normalizeProjectId(project));
    }
  };

  return (
    <aside className="w-full max-w-xs flex-shrink-0 bg-slate-900/60 text-slate-100 rounded-2xl p-4 shadow-xl border border-white/5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold tracking-wide">Проекты</h2>
        <span className="text-xs uppercase text-slate-300">{projects?.length ?? 0}</span>
      </div>

      {isLoading ? (
        <ul className="space-y-2 animate-pulse">
          {Array.from({ length: 4 }).map((_, idx) => (
            <li key={idx} className="h-12 rounded-xl bg-slate-700/50" />
          ))}
        </ul>
      ) : error ? (
        <div className="text-sm text-red-300 bg-red-900/30 border border-red-700/40 rounded-xl p-3">
          {error}
        </div>
      ) : !projects?.length ? (
        <div className="text-sm text-slate-300 bg-slate-800/70 rounded-xl p-3 text-center">
          {emptyMessage}
        </div>
      ) : (
        <ul className="space-y-2 overflow-y-auto max-h-[60vh] pr-1">
          {projects.map((project, index) => {
            const projectId = normalizeProjectId(project);
            const isActive = projectId === activeProjectId;
            const Wrapper = onSelect ? "button" : Link;
            const wrapperProps = onSelect
              ? { type: "button", onClick: () => handleSelect(project) }
              : { to: `/projects/${projectId}` };

            return (
              <li key={projectId ?? `project-${index}`}>
                <Wrapper
                  {...wrapperProps}
                  className={`w-full text-left block px-4 py-3 rounded-xl transition-colors duration-200 border border-transparent focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 focus:ring-indigo-400 ${
                    isActive
                      ? "bg-indigo-500/80 text-white border-indigo-400"
                      : "bg-slate-800/70 hover:bg-slate-700/70"
                  }`}
                >
                  <div className="text-sm font-semibold leading-tight truncate">
                    {project?.title ?? project?.name ?? `Проект ${projectId}`}
                  </div>
                  {project?.description ? (
                    <div className="text-xs text-slate-300 truncate">
                      {project.description}
                    </div>
                  ) : null}
                  {project?.status ? (
                    <div className="mt-1 text-[11px] uppercase tracking-wider text-slate-300">
                      {project.status}
                    </div>
                  ) : null}
                </Wrapper>
              </li>
            );
          })}
        </ul>
      )}
    </aside>
  );
}
