import { useState } from "react";

export default function FileUploadPanel({
  onUpload,
  disabled = false,
  status = "idle",
  statusMessage,
}) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    setError(null);
    if (file && file.type !== "application/pdf") {
      setError("Поддерживаются только PDF-файлы");
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file ?? null);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!selectedFile || !onUpload) return;

    setError(null);
    setIsUploading(true);
    try {
      await onUpload(selectedFile);
      setSelectedFile(null);
    } catch (err) {
      setError(err?.message ?? "Не удалось загрузить файл");
    } finally {
      setIsUploading(false);
    }
  };

  const isBusy = disabled || isUploading || status === "uploading";

  return (
    <section className="bg-slate-900/60 border border-white/5 rounded-2xl p-5 shadow-xl text-slate-100">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Загрузка документа</h2>
        <span className="text-xs uppercase tracking-wider text-slate-300">PDF</span>
      </div>
      <form className="space-y-4" onSubmit={handleSubmit}>
        <label
          className={`flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-4 py-10 transition-colors duration-200 cursor-pointer w-full ${
            selectedFile
              ? "border-emerald-400 bg-emerald-900/20 text-emerald-100"
              : "border-slate-500 bg-slate-800/60 text-slate-300 hover:border-slate-300"
          }`}
        >
          <input
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={handleFileChange}
          />
          <span className="text-sm font-medium">
            {selectedFile ? selectedFile.name : "Выберите или перетащите PDF-файл"}
          </span>
          <span className="text-xs text-slate-300">
            {selectedFile ? `${Math.round(selectedFile.size / 1024)} КБ` : "До 20 МБ"}
          </span>
        </label>

        <div className="flex items-center justify-between gap-3 flex-wrap">
          <button
            type="submit"
            disabled={!selectedFile || isBusy}
            className={`px-5 py-2.5 rounded-xl font-semibold transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 ${
              selectedFile
                ? "bg-emerald-500 hover:bg-emerald-400 text-slate-900 focus:ring-emerald-200"
                : "bg-slate-700 text-slate-300 cursor-not-allowed"
            } ${isBusy ? "opacity-70" : ""}`}
          >
            {isUploading || status === "uploading" ? "Загрузка..." : "Загрузить"}
          </button>

          <div className="flex-1 text-sm text-slate-300">
            {status === "analyzing" ? (
              <span className="text-amber-200">Агент анализирует…</span>
            ) : status === "ready" ? (
              <span className="text-emerald-200">Отчёт обновлён</span>
            ) : status === "error" ? (
              <span className="text-red-300">Произошла ошибка при обработке файла</span>
            ) : (
              statusMessage ?? "Поддерживаются только PDF-файлы"
            )}
          </div>
        </div>

        {error ? (
          <div className="text-sm text-red-300 bg-red-900/30 border border-red-700/40 rounded-xl px-3 py-2">
            {error}
          </div>
        ) : null}
      </form>
    </section>
  );
}
