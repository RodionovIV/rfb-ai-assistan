import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../services/apiClient.js";
import SidebarProjectsList from "../components/SidebarProjectsList";
import ProjectHeader from "../components/ProjectHeader";
import { API_PREFIX } from "../config/api";

const normalizeProjects = (rawProjects) => {
  if (!rawProjects) return [];
  if (
    rawProjects.id ||
    rawProjects.project_id ||
    rawProjects.uuid ||
    rawProjects.slug ||
    rawProjects.name
  ) {
    return [rawProjects];
  }
  const list = Array.isArray(rawProjects)
    ? rawProjects
    : rawProjects.projects ?? Object.values(rawProjects ?? {});

  return list.map((project) => ({
    id: project?.id ?? project?.project_id ?? project?.uuid ?? project?.slug ?? project?.name,
    title: project?.title ?? project?.name ?? project?.display_name ?? "Без названия",
    description: project?.description ?? project?.summary ?? null,
    status: project?.status ?? project?.report_status ?? project?.state ?? null,
    raw: project,
  }));
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [creatingProject, setCreatingProject] = useState(false);

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get(`${API_PREFIX}/projects`);
      const normalized = normalizeProjects(response.data);
      setProjects(normalized);
      setError(null);
    } catch (err) {
      console.error("Failed to load projects", err);
      setError("Не удалось загрузить список проектов. Попробуйте обновить страницу позже.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleCreateProject = useCallback(async () => {
    setCreatingProject(true);
    setError(null);
    try {
      const now = new Date();
      const payload = {
        name: `Новый проект ${now.toLocaleDateString("ru-RU")} ${now.toLocaleTimeString("ru-RU")}`,
      };
      const response = await apiClient.post(`${API_PREFIX}/projects/create`, payload);
      const normalized = normalizeProjects(response.data)?.[0];
      if (normalized) {
        setProjects((prev) => [normalized, ...prev]);
        navigate(`/projects/${normalized.id}`);
      } else if (response.data?.id) {
        navigate(`/projects/${response.data.id}`);
      }
    } catch (err) {
      console.error("Failed to create project", err);
      setError(
        err?.response?.data?.message ??
          "Не удалось создать проект. Попробуйте повторить попытку позже."
      );
    } finally {
      setCreatingProject(false);
    }
  }, [navigate]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white">
      <div className="max-w-6xl mx-auto px-6 py-10 space-y-8">
        <ProjectHeader
          title="Дашборд проектов"
          subtitle="Выберите проект, чтобы загрузить документы, посмотреть отчёт и продолжить диалог с агентом."
          status={loading ? "обновление" : undefined}
          meta={projects.length ? [
            `${projects.length} проектов`,
          ] : undefined}
        />

        <div className="grid gap-8 lg:grid-cols-[320px_1fr]">
          <SidebarProjectsList
            projects={projects}
            isLoading={loading}
            error={error}
            onSelect={(_, projectId) => navigate(`/projects/${projectId}`)}
            emptyMessage={loading ? "Загрузка проектов..." : "Пока нет проектов"}
          />

          <section className="bg-slate-900/60 border border-white/5 rounded-2xl p-6 shadow-xl flex flex-col justify-center text-slate-100">
            <div className="space-y-4 max-w-xl">
              <h2 className="text-2xl font-semibold">Начните с загрузки PDF</h2>
              <p className="text-sm text-slate-300 leading-relaxed">
                Создайте проект, загрузив отчёт, техническую документацию или презентацию в формате PDF. После обработки файл будет доступен для анализа, а агент сможет отвечать на вопросы, опираясь на подготовленный контекст.
              </p>
              <button
                type="button"
                onClick={handleCreateProject}
                disabled={creatingProject}
                className={`inline-flex items-center gap-2 self-start px-5 py-2.5 rounded-xl font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:ring-offset-2 focus:ring-offset-slate-900 ${
                  creatingProject
                    ? "bg-indigo-800 text-slate-300 cursor-not-allowed"
                    : "bg-indigo-500 hover:bg-indigo-400 text-white"
                }`}
              >
                {creatingProject ? "Создаём..." : "Добавить проект"}
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
