import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import SidebarProjectsList from "../components/SidebarProjectsList";
import ProjectHeader from "../components/ProjectHeader";
import FileUploadPanel from "../components/FileUploadPanel";
import ReportViewer from "../components/ReportViewer";
import ProjectChat from "../components/ProjectChat";

const normalizeProject = (project, fallbackId) => ({
  id: project?.id ?? project?.project_id ?? project?.uuid ?? project?.slug ?? fallbackId,
  title: project?.title ?? project?.name ?? project?.display_name ?? `Проект ${fallbackId}`,
  description: project?.description ?? project?.summary ?? "",
  status: project?.status ?? project?.report_status ?? project?.state ?? null,
  report: project?.report ?? project?.analysis ?? project?.summary_text ?? null,
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
      setReportUpdatedAt(normalized.reportUpdatedAt ?? reportUpdatedAt ?? null);

      const reportPayload = options.report ?? payload.report ?? payload.analysis ?? payload.summary_text;
      if (reportPayload) {
        setReport(reportPayload);
        setReportStatus("ready");
      } else if (payload.status === "analyzing" || payload.report_status === "analyzing") {
        setReport(null);
        setReportStatus("analyzing");
      } else if (!options.preserveStatus && reportStatus === "loading") {
        setReportStatus(normalized.status ?? "idle");
      }

      const updatedAtPayload = options.updatedAt ?? payload.updated_at ?? payload.report_updated_at ?? payload.modified_at;
      if (updatedAtPayload) {
        setReportUpdatedAt(updatedAtPayload);
      }

      const contextPayload = options.context ?? payload.context_summary ?? payload.context ?? payload.metadata?.context;
      if (contextPayload) {
        setContextSummary(contextPayload);
      }
    },
    [projectId, reportStatus, reportUpdatedAt]
  );

  const loadProjectsList = useCallback(async () => {
    setSidebarLoading(true);
    setSidebarError(null);
    try {
      const response = await axios.get("/projects");
      const list = normalizeProjectsList(response.data);
      setProjects(list);
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
      try {
        const response = await axios.get(`/projects/${id}`);
        applyProjectData(response.data);
      } catch (err) {
        console.error("Failed to load project", err);
        const message = err?.response?.data?.message ?? "Не удалось загрузить проект";
        setReportStatus("error");
        setReportError(message);
      }
    },
    [applyProjectData]
  );

  const updateChatFromPayload = useCallback(
    (payload) => {
      if (!payload) return;
      const history = normalizeHistory(payload);
      if (history.length) {
        setChatMessages(history);
      }
      if (payload.context_summary ?? payload.context) {
        setContextSummary(payload.context_summary ?? payload.context);
      }
      if (payload.report ?? payload.analysis ?? payload.summary_text) {
        setReport(payload.report ?? payload.analysis ?? payload.summary_text);
        setReportStatus("ready");
      }
      if (payload.updated_at ?? payload.report_updated_at) {
        setReportUpdatedAt(payload.updated_at ?? payload.report_updated_at);
      }
    },
    []
  );

  const loadChatHistory = useCallback(
    async (id) => {
      setChatError(null);
      try {
        const response = await axios.get(`/projects/${id}/chat`);
        updateChatFromPayload(response.data);
      } catch (err) {
        console.error("Failed to load chat history", err);
        setChatError("Не удалось загрузить историю чата");
      }
    },
    [updateChatFromPayload]
  );

  const pollReport = useCallback(
    async (id, attempts = 10, delay = 3000) => {
      for (let attempt = 0; attempt < attempts; attempt += 1) {
        try {
          const response = await axios.get(`/projects/${id}/report`);
          const payload = response.data ?? {};
          if (payload.status) {
            setReportStatus(payload.status);
          }
          if (payload.report ?? payload.analysis ?? payload.summary_text) {
            setReport(payload.report ?? payload.analysis ?? payload.summary_text);
            setReportStatus("ready");
            setReportUpdatedAt(payload.updated_at ?? payload.report_updated_at ?? new Date().toISOString());
            if (payload.context_summary ?? payload.context) {
              setContextSummary(payload.context_summary ?? payload.context);
            }
            return payload;
          }
          if ((payload.status ?? payload.report_status) === "ready") {
            await loadProjectDetails(id, { skipStatusUpdate: true });
            return payload;
          }
        } catch (err) {
          console.error("Report polling failed", err);
        }
        // wait before next attempt
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
      return null;
    },
    [loadProjectDetails]
  );

  const handleUpload = useCallback(
    async (file) => {
      if (!projectId) return;
      const formData = new FormData();
      formData.append("file", file);

      setReportStatus("uploading");
      setReportError(null);

      try {
        await axios.post(`/projects/${projectId}/documents`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        setReportStatus("analyzing");
        await pollReport(projectId);
        await loadProjectDetails(projectId, { skipStatusUpdate: true });
        await loadChatHistory(projectId);
      } catch (err) {
        console.error("File upload failed", err);
        const message = err?.response?.data?.message ?? err?.message ?? "Не удалось загрузить документ";
        setReportStatus("error");
        setReportError(message);
        throw new Error(message);
      }
    },
    [projectId, pollReport, loadProjectDetails, loadChatHistory]
  );

  const handleSendMessage = useCallback(
    async (message) => {
      if (!projectId) return;
      setChatLoading(true);
      setChatError(null);
      try {
        const response = await axios.post(`/projects/${projectId}/chat`, { message });
        const payload = response.data ?? {};
        if (!normalizeHistory(payload).length) {
          setChatMessages((prev) => [
            ...prev,
            { role: "user", content: message },
            { role: "assistant", content: payload.reply ?? payload.answer ?? "" },
          ]);
        } else {
          updateChatFromPayload(payload);
        }
        if (payload.context_summary ?? payload.context) {
          setContextSummary(payload.context_summary ?? payload.context);
        }
        if (payload.report ?? payload.analysis ?? payload.summary_text) {
          setReport(payload.report ?? payload.analysis ?? payload.summary_text);
          setReportStatus("ready");
          setReportUpdatedAt(payload.updated_at ?? payload.report_updated_at ?? new Date().toISOString());
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
    [projectId, updateChatFromPayload]
  );

  useEffect(() => {
    loadProjectsList();
  }, [loadProjectsList]);

  useEffect(() => {
    if (!projectId) return;
    loadProjectDetails(projectId);
    loadChatHistory(projectId);
  }, [projectId, loadProjectDetails, loadChatHistory]);

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
            emptyMessage={sidebarLoading ? "Загрузка..." : "Проекты ещё не созданы"}
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
