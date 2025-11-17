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
  rating: typeof project?.rating === "number" ? project.rating : project?.score ?? null,
  ratingComment:
    project?.rating_comment ?? project?.ratingComment ?? project?.feedback ?? null,
  files: Array.isArray(project?.files)
    ? project.files
    : project?.documents ?? project?.document_paths ?? [],
});

const normalizeHistory = (payload) => {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  return payload.history ?? payload.messages ?? payload.chat ?? [];
};

const RATING_VALUES = [1, 2, 3, 4, 5];

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
  const [deletingProject, setDeletingProject] = useState(false);
  const [renamingProject, setRenamingProject] = useState(false);
  const [renameError, setRenameError] = useState(null);
  const fileInputRef = useRef(null);
  const documentFilenameSourceRef = useRef(null);
  const [documentFilename, setDocumentFilename] = useState(null);
  const [isDocumentPanelCollapsed, setIsDocumentPanelCollapsed] = useState(false);
  const [isRatingModalOpen, setIsRatingModalOpen] = useState(false);
  const [ratingValue, setRatingValue] = useState(5);
  const [ratingComment, setRatingComment] = useState("");
  const [ratingSubmitting, setRatingSubmitting] = useState(false);
  const [ratingError, setRatingError] = useState(null);

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

  const hasProjectRating = typeof project?.rating === "number";
  const canShowRatingButton = reportStatus === "ready" && Boolean(report);

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

  const handleOpenRatingModal = useCallback(() => {
    setRatingValue(typeof project?.rating === "number" ? project.rating : 5);
    setRatingComment(project?.ratingComment ?? "");
    setRatingError(null);
    setIsRatingModalOpen(true);
  }, [project?.rating, project?.ratingComment]);

  const handleEditRating = useCallback(() => {
    if (!hasProjectRating) return;
    handleOpenRatingModal();
  }, [hasProjectRating, handleOpenRatingModal]);

  const handleRatingPreviewKeyDown = useCallback(
    (event) => {
      if (!hasProjectRating) return;
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        handleOpenRatingModal();
      }
    },
    [hasProjectRating, handleOpenRatingModal]
  );

  const handleCloseRatingModal = useCallback(() => {
    setIsRatingModalOpen(false);
    setRatingError(null);
  }, []);

  const handleSubmitRating = useCallback(
    async (event) => {
      event?.preventDefault?.();
      if (!projectId) return;
      if (!ratingValue) {
        setRatingError("Пожалуйста, выберите количество звёзд");
        return;
      }
      setRatingSubmitting(true);
      setRatingError(null);
      try {
        const payload = { rating: ratingValue };
        const trimmedComment = ratingComment.trim();
        if (trimmedComment) {
          payload.comment = trimmedComment;
        }
        const response = await apiClient.post(`${API_PREFIX}/projects/${projectId}/rate`, payload);
        applyProjectData(response.data, { preserveStatus: true });
        const successMessage = hasProjectRating ? "Отзыв обновлён" : "Спасибо за оценку!";
        setDocumentActionMessage(successMessage);
        setDocumentActionError(null);
        setIsRatingModalOpen(false);
      } catch (err) {
        const message =
          err?.response?.data?.detail ??
          err?.response?.data?.message ??
          err?.message ??
          "Не удалось отправить оценку";
        setRatingError(message);
      } finally {
        setRatingSubmitting(false);
      }
    },
    [projectId, ratingValue, ratingComment, applyProjectData, hasProjectRating]
  );

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

  const isChatAvailable = useMemo(
    () => reportStatus === "ready" && Boolean(report),
    [reportStatus, report]
  );

  const shouldEnableDocumentCollapse = isChatAvailable;

  useEffect(() => {
    setIsDocumentPanelCollapsed(shouldEnableDocumentCollapse);
  }, [shouldEnableDocumentCollapse]);

  const DocumentPanelHeader = shouldEnableDocumentCollapse ? "button" : "div";

  const toggleDocumentPanel = useCallback(() => {
    if (!shouldEnableDocumentCollapse) return;
    setIsDocumentPanelCollapsed((prev) => !prev);
  }, [shouldEnableDocumentCollapse]);
  const mainLayoutClasses = useMemo(() => {
    if (isChatAvailable) {
      return "flex flex-col lg:flex-row gap-8 lg:items-start";
    }
    return "flex flex-col items-stretch";
  }, [isChatAvailable]);

  const documentPanelBodyClasses = useMemo(() => {
    const classes = ["flex flex-col gap-4"];
    if (shouldEnableDocumentCollapse) {
      classes.push("lg:transition-all lg:duration-300 lg:ease-out");
      if (isDocumentPanelCollapsed) {
        classes.push(
          "lg:max-h-0 lg:opacity-0 lg:overflow-hidden lg:pointer-events-none lg:translate-x-4"
        );
      } else {
        classes.push("lg:max-h-none lg:opacity-100 lg:translate-x-0");
      }
    }
    return classes.join(" ");
  }, [isDocumentPanelCollapsed, shouldEnableDocumentCollapse]);

  const documentPanelClasses = useMemo(() => {
    const classes = [
      "bg-slate-900/60 border border-white/5 rounded-2xl shadow-xl text-slate-100 flex flex-col transition-all duration-300 ease-out p-5",
    ];

    if (isChatAvailable) {
      classes.push("lg:flex-shrink-0 lg:self-start");
    } else {
      classes.push("w-full max-w-2xl mx-auto");
    }

    if (!shouldEnableDocumentCollapse) {
      classes.push("gap-4");
      if (isChatAvailable) {
        classes.push("lg:w-[470px]");
      }
      return classes.join(" ");
    }

    if (isDocumentPanelCollapsed) {
      classes.push("gap-3 lg:gap-2 lg:w-[82px] lg:px-3 lg:py-4 lg:items-center");
    } else {
      classes.push("gap-4 lg:w-[480px] lg:px-5");
    }

    return classes.join(" ");
  }, [
    isChatAvailable,
    isDocumentPanelCollapsed,
    shouldEnableDocumentCollapse,
  ]);

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

        <div className={mainLayoutClasses}>
          {isChatAvailable ? (
            <div className="flex-1 min-w-0 flex">
              <ProjectChat
                messages={chatMessages}
                onSend={handleSendMessage}
                isSending={chatLoading}
                error={chatError}
              />
            </div>
          ) : null}

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
                  } hidden flex-col items-center gap-1 text-center text-[11px] text-slate-300 py-2`}
                >
                  <span
                    className="text-[10px] font-semibold tracking-[0.25em] uppercase text-slate-100"
                    style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}
                  >
                    Документ проекта
                  </span>
                  <span className="inline-flex h-5 w-5 text-[10px] items-center justify-center rounded-full bg-slate-800/80 border border-white/10 rotate-90" aria-hidden="true">
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

              <div className="flex flex-nowrap items-stretch gap-3 overflow-x-auto">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={reportStatus === "uploading" || reportStatus === "analyzing"}
                  className={`px-3.5 py-2 text-sm rounded-xl font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 ${
                    reportStatus === "uploading" || reportStatus === "analyzing"
                      ? "bg-slate-800 text-slate-400 cursor-not-allowed"
                      : "bg-indigo-500 hover:bg-indigo-400 text-white focus:ring-indigo-300"
                  }`}
                >
                  {reportStatus === "uploading" ? "Загружаем..." : "Загрузить"}
                </button>
                {canShowRatingButton ? (
                  <button
                    type="button"
                    onClick={!hasProjectRating ? handleOpenRatingModal : undefined}
                    onDoubleClick={hasProjectRating ? handleEditRating : undefined}
                    onKeyDown={hasProjectRating ? handleRatingPreviewKeyDown : undefined}
                    className={`inline-flex items-center justify-center rounded-xl border px-3.5 py-2 text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 w-48 min-w-[12rem] max-w-[12rem] text-center truncate ${
                      hasProjectRating
                        ? "bg-slate-800/70 border-white/10 text-slate-200 hover:bg-slate-800 focus:ring-amber-300/40"
                        : "bg-emerald-500 text-white border-emerald-400 hover:bg-emerald-400 focus:ring-emerald-200"
                    }`}
                    title={
                      hasProjectRating
                        ? "Дважды нажмите, чтобы изменить отзыв"
                        : "Оцените проект"
                    }
                  >
                    <span className="text-sm font-semibold text-inherit">
                      Поставить оценку
                    </span>
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={handleDeleteProject}
                  disabled={deletingProject}
                  className={`px-3.5 py-2 text-sm rounded-xl font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 ${
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
      {isRatingModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4 py-6 bg-slate-950/70 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-slate-900 border border-white/10 rounded-3xl shadow-2xl text-slate-100 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-semibold">Оцените проект</h3>
              <button
                type="button"
                onClick={handleCloseRatingModal}
                className="text-slate-400 hover:text-slate-100 transition-colors"
                aria-label="Закрыть форму оценки"
              >
                ×
              </button>
            </div>
            <form className="space-y-4" onSubmit={handleSubmitRating}>
              <label className="flex flex-col gap-2 text-sm">
                <span className="uppercase tracking-widest text-slate-400">Комментарий</span>
                <textarea
                  value={ratingComment}
                  onChange={(event) => setRatingComment(event.target.value)}
                  rows={4}
                  placeholder="Поделитесь впечатлениями от работы с проектом"
                  className="w-full rounded-2xl bg-slate-950/40 border border-white/10 px-4 py-3 text-base text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-300"
                />
              </label>
              <div className="space-y-3">
                <p className="text-sm uppercase tracking-widest text-slate-400">Оценка</p>
                <div className="flex items-center justify-center gap-2">
                  {RATING_VALUES.map((value) => {
                    const isActive = value <= ratingValue;
                    return (
                      <button
                        key={value}
                        type="button"
                        onClick={() => setRatingValue(value)}
                        className={`h-12 w-12 rounded-2xl border transition-colors ${
                          isActive
                            ? "bg-amber-400/20 border-amber-300 text-amber-200"
                            : "bg-slate-900/60 border-white/10 text-slate-500"
                        }`}
                        aria-label={`Поставить ${value} ${value === 1 ? "звезду" : "звёзды"}`}
                      >
                        <span className="text-2xl" aria-hidden="true">
                          {isActive ? "★" : "☆"}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
              {ratingError ? (
                <div className="text-sm text-red-200 bg-red-900/40 border border-red-700/40 rounded-2xl px-4 py-2">
                  {ratingError}
                </div>
              ) : null}
              <div className="flex flex-wrap justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleCloseRatingModal}
                  className="px-4 py-2 rounded-2xl border border-white/10 text-slate-200 hover:bg-slate-800/70"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={!ratingValue || ratingSubmitting}
                  className={`px-5 py-2 rounded-2xl font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 ${
                    !ratingValue || ratingSubmitting
                      ? "bg-amber-900/30 text-amber-200 cursor-not-allowed"
                      : "bg-amber-400 text-slate-900 hover:bg-amber-300 focus:ring-amber-200"
                  }`}
                >
                  {ratingSubmitting ? "Отправляем..." : "Оценить"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
