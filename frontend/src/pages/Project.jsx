import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import apiClient from "../services/apiClient.js";
import ProjectHeader from "../components/ProjectHeader";
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

const getLatestDocumentName = (files) => {
  if (!Array.isArray(files) || !files.length) {
    return null;
  }
  const last = files[files.length - 1];
  if (!last) {
    return null;
  }
  const rawValue =
    typeof last === "string"
      ? last
      : last?.original_name ??
        last?.filename ??
        last?.name ??
        last?.path ??
        last?.stored_path ??
        null;
  if (!rawValue) {
    return null;
  }
  const segments = `${rawValue}`.split(/[\\/]/);
  return segments[segments.length - 1] || rawValue;
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
  files: Array.isArray(project?.files)
    ? project.files
    : project?.documents ?? project?.document_paths ?? [],
});

const normalizeHistory = (payload) => {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  return payload.history ?? payload.messages ?? payload.chat ?? [];
};

export default function Project() {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [reportStatus, setReportStatus] = useState("loading");
  const [report, setReport] = useState(null);
  const [reportUpdatedAt, setReportUpdatedAt] = useState(null);
  const [reportError, setReportError] = useState(null);

  const [chatMessages, setChatMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState(null);
  const [documentActionMessage, setDocumentActionMessage] = useState(null);
  const [documentActionError, setDocumentActionError] = useState(null);
  const [savingProject, setSavingProject] = useState(false);
  const [deletingProject, setDeletingProject] = useState(false);
  const [renamingProject, setRenamingProject] = useState(false);
  const [renameError, setRenameError] = useState(null);
  const fileInputRef = useRef(null);
  const documentFilenameSourceRef = useRef(null);
  const [documentFilename, setDocumentFilename] = useState(null);
  const [isDocumentPanelCollapsed, setIsDocumentPanelCollapsed] = useState(false);

  const resetDocumentFilename = useCallback(() => {
    documentFilenameSourceRef.current = null;
    setDocumentFilename(null);
  }, []);

  const setDocumentFilenameFromServer = useCallback(
    (name) => {
      if (documentFilenameSourceRef.current === "upload") {
        return;
      }
      if (!name) {
        resetDocumentFilename();
        return;
      }
      documentFilenameSourceRef.current = "server";
      setDocumentFilename(name);
    },
    [resetDocumentFilename]
  );

  const setDocumentFilenameFromUpload = useCallback(
    (name) => {
      if (!name) {
        resetDocumentFilename();
        return;
      }
      documentFilenameSourceRef.current = "upload";
      setDocumentFilename(name);
    },
    [resetDocumentFilename]
  );

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

      const latestFileName = getLatestDocumentName(normalized.files);
      if (latestFileName) {
        setDocumentFilenameFromServer(latestFileName);
      } else {
        setDocumentFilenameFromServer(null);
      }

      if (!options.preserveStatus) {
        setReportStatus((prevStatus) => {
          if (normalized.status) {
            return normalized.status;
          }
          if (prevStatus === "loading") {
            return "idle";
          }
          return prevStatus;
        });
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

      return normalized;
    },
    [projectId, setDocumentFilenameFromServer]
  );

  const updateChatFromPayload = useCallback((payload) => {
    if (!payload) {
      setChatMessages([]);
      return;
    }

    const history = normalizeHistory(payload);
    setChatMessages(history.length ? history : []);

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

  const processProject = useCallback(
    async (id) => {
      if (!id) return null;
      setReportStatus("analyzing");
      try {
        const response = await apiClient.post(`${API_PREFIX}/projects/${id}/process`);
        const payload = response.data ?? {};
        if (payload.details) {
          setReport(payload.details);
          setReportUpdatedAt(new Date().toISOString());
        }
        setReportStatus("ready");
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
      if (!projectId) return null;
      const formData = new FormData();
      formData.append("file", file);

      setReportStatus("uploading");
      setReportError(null);

      try {
        setReportStatus("analyzing");
        const response = await apiClient.post(`${API_PREFIX}/projects/${projectId}/upload`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        const payload = response.data ?? {};
        if (payload.project) {
          applyProjectData(payload.project, { preserveStatus: true });
          updateChatFromPayload(payload.project);
        }
        setReportStatus("ready");
        setReportUpdatedAt(new Date().toISOString());
        return payload;
      } catch (err) {
        console.error("File upload failed", err);
        const message = err?.response?.data?.message ?? err?.message ?? "Не удалось загрузить документ";
        setReportStatus("error");
        setReportError(message);
        throw new Error(message);
      }
    },
    [projectId, applyProjectData, updateChatFromPayload]
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

  const handleDocumentUploadChange = useCallback(
    async (event) => {
      const file = event.target.files?.[0];
      if (!file) return;
      setDocumentActionMessage(null);
      setDocumentActionError(null);
      try {
        const uploadResponse = await handleUpload(file);
        const uploadedName =
          uploadResponse?.original_name ?? uploadResponse?.filename ?? file.name;
        setDocumentFilenameFromUpload(uploadedName);
        setDocumentActionMessage("Документ загружен");
      } catch (err) {
        setDocumentActionError(err?.message ?? "Не удалось загрузить документ");
      } finally {
        event.target.value = "";
      }
    },
    [handleUpload, setDocumentFilenameFromUpload]
  );

  const handleSaveProject = useCallback(async () => {
    if (!projectId) return;
    setSavingProject(true);
    setDocumentActionMessage(null);
    setDocumentActionError(null);
    try {
      await processProject(projectId);
      await loadProjectDetails(projectId, { skipStatusUpdate: true });
      setDocumentActionMessage("Проект сохранён");
    } catch (err) {
      const message =
        err?.response?.data?.message ?? err?.message ?? "Не удалось сохранить проект";
      setDocumentActionError(message);
    } finally {
      setSavingProject(false);
    }
  }, [loadProjectDetails, processProject, projectId]);

  const handleDeleteProject = useCallback(async () => {
    if (!projectId) return;
    if (typeof window !== "undefined") {
      const confirmed = window.confirm(
        "Удалить проект? Это действие нельзя отменить."
      );
      if (!confirmed) {
        return;
      }
    }
    setDeletingProject(true);
    setDocumentActionMessage(null);
    setDocumentActionError(null);
    try {
      await apiClient.delete(`${API_PREFIX}/projects/${projectId}`);
      navigate("/", { replace: true });
    } catch (err) {
      const message = err?.response?.data?.message ?? err?.message ?? "Не удалось удалить проект";
      setDocumentActionError(message);
    } finally {
      setDeletingProject(false);
    }
  }, [navigate, projectId]);

  const handleRenameProject = useCallback(
    async (nextTitle) => {
      if (!projectId) return null;
      const trimmedTitle = `${nextTitle ?? ""}`.trim();
      if (!trimmedTitle) {
        const message = "Название не может быть пустым";
        setRenameError(message);
        throw new Error(message);
      }
      setRenamingProject(true);
      setRenameError(null);
      try {
        const response = await apiClient.post(`${API_PREFIX}/projects/update`, {
          project_id: projectId,
          name: trimmedTitle,
        });
        const normalized = applyProjectData(response.data, { preserveStatus: true });
        return normalized;
      } catch (err) {
        const message =
          err?.response?.data?.detail ??
          err?.response?.data?.message ??
          err?.message ??
          "Не удалось обновить название проекта";
        setRenameError(message);
        throw new Error(message);
      } finally {
        setRenamingProject(false);
      }
    },
    [applyProjectData, projectId]
  );

  const handleDismissRenameError = useCallback(() => {
    setRenameError(null);
  }, []);

  useEffect(() => {
    if (!projectId) return;
    loadProjectDetails(projectId);
  }, [projectId, loadProjectDetails]);

  useEffect(() => {
    setDocumentActionMessage(null);
    setDocumentActionError(null);
  }, [projectId]);

  useEffect(() => {
    resetDocumentFilename();
  }, [projectId, resetDocumentFilename]);

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

  const documentUpdatedAtLabel = useMemo(() => {
    if (!reportUpdatedAt) return null;
    try {
      const date = new Date(reportUpdatedAt);
      if (Number.isNaN(date.getTime?.())) {
        return null;
      }
      return date.toLocaleString();
    } catch (err) {
      console.warn("Unable to format updated date", reportUpdatedAt, err);
      return null;
    }
  }, [reportUpdatedAt]);

  const shouldEnableDocumentCollapse = useMemo(
    () => reportStatus === "ready" && Boolean(report),
    [reportStatus, report]
  );

  useEffect(() => {
    setIsDocumentPanelCollapsed(shouldEnableDocumentCollapse);
  }, [shouldEnableDocumentCollapse]);

  const DocumentPanelHeader = shouldEnableDocumentCollapse ? "button" : "div";

  const toggleDocumentPanel = useCallback(() => {
    if (!shouldEnableDocumentCollapse) return;
    setIsDocumentPanelCollapsed((prev) => !prev);
  }, [shouldEnableDocumentCollapse]);

  const documentPanelBodyClasses = useMemo(() => {
    const classes = ["flex flex-col gap-4"];
    if (shouldEnableDocumentCollapse) {
      classes.push(
        "lg:transition-all lg:duration-300 lg:ease-out lg:overflow-hidden"
      );
      if (isDocumentPanelCollapsed) {
        classes.push(
          "lg:opacity-0 lg:pointer-events-none lg:translate-x-4"
        );
      } else {
        classes.push("lg:opacity-100 lg:translate-x-0");
      }
    }
    return classes.join(" ");
  }, [isDocumentPanelCollapsed, shouldEnableDocumentCollapse]);

  const documentPanelClasses = useMemo(() => {
    const base =
      "bg-slate-900/60 border border-white/5 rounded-2xl shadow-xl text-slate-100 flex flex-col gap-4 transition-all duration-300 ease-out p-5 lg:flex-shrink-0";
    if (!shouldEnableDocumentCollapse) {
      return `${base} lg:w-[470px]`;
    }
    return `${base} ${
      isDocumentPanelCollapsed
        ? "lg:w-[90px] lg:px-3 lg:items-center"
        : "lg:w-[480px] lg:px-5"
    }`;
  }, [isDocumentPanelCollapsed, shouldEnableDocumentCollapse]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white">
      <div className="max-w-7xl mx-auto px-6 py-10 space-y-8">
        <ProjectHeader
          title={project?.title ?? `Проект ${projectId}`}
          subtitle={project?.description ?? "Загрузите документ, чтобы агент подготовит отчёт и контекст для чата."}
          status={statusLabel}
          onBack={() => navigate("/")}
          meta={meta}
          onRename={handleRenameProject}
          isRenamingTitle={renamingProject}
          renameError={renameError}
          onDismissRenameError={handleDismissRenameError}
        />

        <div className="flex flex-col lg:flex-row gap-8">
          <div className="flex-1 min-w-0">
            <ProjectChat
              messages={chatMessages}
              onSend={handleSendMessage}
              isSending={chatLoading}
              error={chatError}
            />
          </div>

          <section className={documentPanelClasses}>
            <DocumentPanelHeader
              type={shouldEnableDocumentCollapse ? "button" : undefined}
              onClick={toggleDocumentPanel}
              aria-expanded={shouldEnableDocumentCollapse ? !isDocumentPanelCollapsed : undefined}
              className={`flex flex-wrap items-start justify-between gap-4 text-left ${
                shouldEnableDocumentCollapse
                  ? "cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:ring-offset-2 focus:ring-offset-slate-900 rounded-xl px-2 -mx-2"
                  : ""
              }`}
            >
              <div
                className={`${
                  shouldEnableDocumentCollapse && isDocumentPanelCollapsed
                    ? "lg:hidden"
                    : ""
                } flex-1 min-w-0`}
              >
                <h2 className="text-lg font-semibold">Документ проекта</h2>
                {documentFilename ? (
                  <p
                    className="text-sm text-slate-100 font-medium truncate max-w-xs"
                    title={documentFilename}
                  >
                    {documentFilename}
                  </p>
                ) : (
                  <p className="text-sm text-slate-300">
                    Управляйте загрузкой файла, сохранением отчёта и удалением проекта.
                  </p>
                )}
              </div>
              <div
                className={`${
                  shouldEnableDocumentCollapse && isDocumentPanelCollapsed
                    ? "lg:hidden"
                    : ""
                } flex items-center gap-3 text-xs text-slate-300`}
              >
                {documentUpdatedAtLabel ? <span>Обновлено: {documentUpdatedAtLabel}</span> : null}
                {shouldEnableDocumentCollapse ? (
                  <span
                    className={`inline-flex h-6 w-6 items-center justify-center rounded-full bg-slate-800/80 border border-white/10 transition-transform ${
                      isDocumentPanelCollapsed ? "lg:rotate-90 rotate-180" : "lg:-rotate-90 rotate-0"
                    }`}
                    aria-hidden="true"
                  >
                    ↓
                  </span>
                ) : null}
              </div>
              {shouldEnableDocumentCollapse ? (
                <div
                  className={`${
                    isDocumentPanelCollapsed ? "lg:flex" : "lg:hidden"
                  } hidden flex-col items-center gap-3 text-center text-xs text-slate-300`}
                >
                  <span
                    className="text-sm font-semibold tracking-[0.3em] text-slate-100"
                    style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}
                  >
                    Документ проекта
                  </span>
                  <span className="text-[11px] text-slate-400">Нажмите, чтобы открыть</span>
                  <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-slate-800/80 border border-white/10 transition-transform rotate-90" aria-hidden="true">
                    ↓
                  </span>
                </div>
              ) : null}
            </DocumentPanelHeader>

            <div className={documentPanelBodyClasses}>
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={handleDocumentUploadChange}
              />

              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={reportStatus === "uploading" || reportStatus === "analyzing"}
                  className={`px-4 py-2.5 rounded-xl font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 ${
                    reportStatus === "uploading" || reportStatus === "analyzing"
                      ? "bg-slate-800 text-slate-400 cursor-not-allowed"
                      : "bg-indigo-500 hover:bg-indigo-400 text-white focus:ring-indigo-300"
                  }`}
                >
                  {reportStatus === "uploading" ? "Загружаем..." : "Загрузить"}
                </button>
                <button
                  type="button"
                  onClick={handleSaveProject}
                  disabled={savingProject}
                  className={`px-4 py-2.5 rounded-xl font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 ${
                    savingProject
                      ? "bg-emerald-800 text-emerald-200 cursor-not-allowed"
                      : "bg-emerald-500 hover:bg-emerald-400 text-slate-900 focus:ring-emerald-200"
                  }`}
                >
                  {savingProject ? "Сохраняем..." : "Сохранить проект"}
                </button>
                <button
                  type="button"
                  onClick={handleDeleteProject}
                  disabled={deletingProject}
                  className={`px-4 py-2.5 rounded-xl font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 ${
                    deletingProject
                      ? "bg-red-900/60 text-red-200 cursor-not-allowed"
                      : "bg-red-600 hover:bg-red-500 text-white focus:ring-red-300"
                  }`}
                >
                  {deletingProject ? "Удаляем..." : "Удалить"}
                </button>
              </div>

              {documentActionError ? (
                <div className="text-sm text-red-300 bg-red-900/30 border border-red-700/40 rounded-xl px-3 py-2">
                  {documentActionError}
                </div>
              ) : null}

              {documentActionMessage ? (
                <div className="text-sm text-emerald-200 bg-emerald-900/20 border border-emerald-700/40 rounded-xl px-3 py-2">
                  {documentActionMessage}
                </div>
              ) : null}

              <div className="pt-3 border-t border-white/5">
                <ReportViewer
                  report={report}
                  status={reportStatus}
                  updatedAt={reportUpdatedAt}
                  error={reportError}
                  hideHeader
                  bare
                />
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
