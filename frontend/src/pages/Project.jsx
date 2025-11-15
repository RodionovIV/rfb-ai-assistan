import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import apiClient from "../services/apiClient.js";
import SidebarProjectsList from "../components/SidebarProjectsList";
import ProjectHeader from "../components/ProjectHeader";
import FileUploadPanel from "../components/FileUploadPanel";
import ReportViewer from "../components/ReportViewer";
import ProjectChat from "../components/ProjectChat";
import { API_PREFIX } from "../config/api";

const extractReport = (payload) => {
  if (!payload) return null;
  return (
    payload.report ??
    payload.analysis ??
    payload.summary_text ??
    payload.analysis_summary ??
    null
  );
};

const normalizeProject = (project, fallbackId) => ({
  id: project?.id ?? project?.project_id ?? project?.uuid ?? project?.slug ?? fallbackId,
  title: project?.title ?? project?.name ?? project?.display_name ?? `Проект ${fallbackId}`,
  description: project?.description ?? project?.summary ?? "",
  status:
    project?.status ??
    project?.report_status ??
    project?.state ??
    (project?.processed ? "ready" : null),
  report: extractReport(project),
  reportUpdatedAt: project?.updated_at ?? project?.report_updated_at ?? project?.modified_at ?? null,
  context: project?.context_summary ?? project?.context ?? project?.metadata?.context ?? null,
});

const normalizeHistory = (payload) => {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  return payload.history ?? payload.messages ?? payload.chat ?? [];
};

const normalizeProjectsList = (data) => {
  if (!data) return [];
  const list = Array.isArray(data) ? data : data.projects ?? Object.values(data ?? {});
  return list.map((item) => normalizeProject(item, item?.id ?? item?.project_id));
};

export default function Project() {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [projects, setProjects] = useState([]);
  const [sidebarLoading, setSidebarLoading] = useState(false);
  const [sidebarError, setSidebarError] = useState(null);

  const [project, setProject] = useState(null);
  const [reportStatus, setReportStatus] = useState("loading");
  const [report, setReport] = useState(null);
  const [reportUpdatedAt, setReportUpdatedAt] = useState(null);
  const [reportError, setReportError] = useState(null);

  const [chatMessages, setChatMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState(null);
  const [contextSummary, setContextSummary] = useState(null);

  const statusLabel = useMemo(() => {
    if (project?.status) return project.status;
    switch (reportStatus) {
      case "loading":
        return "загрузка";
      case "uploading":
        return "загрузка файла";
      case "analyzing":
        return "анализ";
      case "ready":
        return "готов";
      case "error":
        return "ошибка";
      default:
        return null;
    }
  }, [project?.status, reportStatus]);

  const applyProjectData = useCallback(
    (payload, options = {}) => {
      if (!payload) return;
      const normalized = normalizeProject(payload, projectId);
      setProject(normalized);

      if (!options.preserveStatus) {
        if (normalized.status) {
          setReportStatus(normalized.status);
        } else if (reportStatus === "loading") {
          setReportStatus("idle");
        }
      }

      const reportPayload = options.report ?? extractReport(payload);
      if (reportPayload) {
        setReport(reportPayload);
        if (!options.preserveStatus) {
          setReportStatus("ready");
        }
      } else if (!options.preserveStatus) {
        setReport(null);
      }

      const updatedAtPayload =
        options.updatedAt ??
        normalized.reportUpdatedAt ??
        payload.updated_at ??
        payload.report_updated_at ??
        payload.modified_at ??
        null;
      if (updatedAtPayload) {
        setReportUpdatedAt(updatedAtPayload);
      }

      const contextPayload =
        options.context ??
        payload.context_summary ??
        payload.context ??
        payload.metadata?.context ??
        undefined;
      if (contextPayload !== undefined) {
        setContextSummary(contextPayload ?? null);
      }
    },
    [projectId, reportStatus]
  );

  const loadProjectsList = useCallback(async () => {
    setSidebarLoading(true);
    setSidebarError(null);
    try {
      const response = await apiClient.get(`${API_PREFIX}/projects`);
      const list = normalizeProjectsList(response.data);
      setProjects(list);
      setSidebarError(null);
    } catch (err) {
      console.error("Failed to load projects list", err);
      setSidebarError("Не удалось загрузить список проектов");
    } finally {
      setSidebarLoading(false);
    }
  }, []);

  const loadProjectDetails = useCallback(
    async (id, { skipStatusUpdate = false } = {}) => {
      if (!skipStatusUpdate) {
        setReportStatus("loading");
      }
      setReportError(null);
      setChatError(null);
      try {
        const response = await apiClient.get(`${API_PREFIX}/projects/${id}`);
        applyProjectData(response.data);
        updateChatFromPayload(response.data);
      } catch (err) {
        console.error("Failed to load project", err);
        const message = err?.response?.data?.message ?? "Не удалось загрузить проект";
        setReportStatus("error");
        setReportError(message);
        setChatError("Не удалось загрузить историю чата");
      }
    },
    [applyProjectData, updateChatFromPayload]
  );

  const updateChatFromPayload = useCallback((payload) => {
    if (!payload) {
      setChatMessages([]);
      setContextSummary(null);
      return;
    }

    const history = normalizeHistory(payload);
    setChatMessages(history.length ? history : []);

    const contextPayload =
      payload.context_summary ??
      payload.context ??
      payload.project?.context_summary ??
      payload.project?.context ??
      null;
    setContextSummary(contextPayload ?? null);

    const reportPayload = extractReport(payload) ?? extractReport(payload.project);
    if (reportPayload) {
      setReport(reportPayload);
      setReportStatus("ready");
    }

    const updatedAtPayload =
      payload.updated_at ??
      payload.report_updated_at ??
      payload.project?.updated_at ??
      payload.project?.report_updated_at ??
      null;
    if (updatedAtPayload) {
      setReportUpdatedAt(updatedAtPayload);
    }
  }, []);

  const processProject = useCallback(
    async (id) => {
      try {
        const response = await apiClient.post(`${API_PREFIX}/projects/${id}/process`);
        const payload = response.data ?? {};
        if (payload.status) {
          setReportStatus(payload.status);
        }
        if (payload.details) {
          setReport(payload.details);
          setReportStatus("ready");
          setReportUpdatedAt(new Date().toISOString());
        }
        return payload;
      } catch (err) {
        console.error("Project processing failed", err);
        const message = err?.response?.data?.message ?? "Не удалось обработать проект";
        setReportStatus("error");
        setReportError(message);
        throw err;
      }
    },
    []
  );

  const handleUpload = useCallback(
    async (file) => {
      if (!projectId) return;
      const formData = new FormData();
      formData.append("file", file);

      setReportStatus("uploading");
      setReportError(null);

      try {
        await apiClient.post(`${API_PREFIX}/projects/${projectId}/upload`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        setReportStatus("analyzing");
        await processProject(projectId);
        await loadProjectDetails(projectId, { skipStatusUpdate: true });
      } catch (err) {
        console.error("File upload failed", err);
        const message = err?.response?.data?.message ?? err?.message ?? "Не удалось загрузить документ";
        setReportStatus("error");
        setReportError(message);
        throw new Error(message);
      }
    },
    [projectId, processProject, loadProjectDetails]
  );

  const handleSendMessage = useCallback(
    async (message) => {
      if (!projectId) return;
      setChatLoading(true);
      setChatError(null);
      try {
        const response = await apiClient.post(`${API_PREFIX}/projects/${projectId}/chat`, { message });
        const payload = response.data ?? {};
        if (payload.project) {
          applyProjectData(payload.project, { preserveStatus: true });
        }
        if (!normalizeHistory(payload).length) {
          setChatMessages((prev) => [
            ...prev,
            { role: "user", content: message },
            { role: "assistant", content: payload.reply ?? payload.answer ?? "" },
          ]);
        } else {
          updateChatFromPayload(payload);
        }
      } catch (err) {
        console.error("Failed to send message", err);
        const messageText = err?.response?.data?.message ?? err?.message ?? "Не удалось отправить сообщение";
        setChatError(messageText);
        throw new Error(messageText);
      } finally {
        setChatLoading(false);
      }
    },
    [projectId, applyProjectData, updateChatFromPayload]
  );

  useEffect(() => {
    loadProjectsList();
  }, [loadProjectsList]);

  useEffect(() => {
    if (!projectId) return;
    loadProjectDetails(projectId);
  }, [projectId, loadProjectDetails]);

  const meta = useMemo(() => {
    const chips = [];
    if (projectId) chips.push(`ID: ${projectId}`);
    if (reportUpdatedAt) {
      try {
        const formatted = new Date(reportUpdatedAt).toLocaleString();
        chips.push(`Обновлено: ${formatted}`);
      } catch (err) {
        console.warn("Unable to format date", reportUpdatedAt, err);
      }
    }
    return chips;
  }, [projectId, reportUpdatedAt]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white">
      <div className="max-w-7xl mx-auto px-6 py-10 space-y-8">
        <ProjectHeader
          title={project?.title ?? `Проект ${projectId}`}
          subtitle={project?.description ?? "Загрузите документ, чтобы агент подготовил отчёт и контекст для чата."}
          status={statusLabel}
          onBack={() => navigate("/")}
          meta={meta}
        />

        <div className="grid gap-8 lg:grid-cols-[320px_minmax(0,1fr)]">
          <SidebarProjectsList
            projects={projects}
            activeProjectId={projectId}
            isLoading={sidebarLoading}
            error={sidebarError}
            onSelect={(_, id) => navigate(`/projects/${id}`)}
            emptyMessage={sidebarLoading ? "Загрузка..." : "Пока нет проектов"}
          />

          <div className="space-y-6">
            <div className="grid gap-6 xl:grid-cols-2">
              <FileUploadPanel
                onUpload={handleUpload}
                status={reportStatus}
                statusMessage={reportError ?? "Загрузите PDF-документ для анализа"}
              />
              <ReportViewer
                report={report}
                status={reportStatus}
                updatedAt={reportUpdatedAt}
                error={reportError}
              />
            </div>

            <ProjectChat
              messages={chatMessages}
              onSend={handleSendMessage}
              isSending={chatLoading}
              contextSummary={contextSummary}
              error={chatError}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
