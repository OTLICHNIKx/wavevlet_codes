import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, ImportCsvError } from "../api";

type ImportMode = "package" | "csv";

export function ImportExperimentPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<ImportMode>("package");
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  const submit = () => {
    if (!file) {
      setErrors(["Выберите файл"]);
      return;
    }
    const effectiveName = name.trim() || file.name.replace(/\.(csv|zip|waveexp)$/i, "");
    setBusy(true);
    setErrors([]);
    const upload = mode === "package"
      ? api.importPackage(file, effectiveName, description)
      : api.importCsv(file, effectiveName, description);
    upload
      .then(experiment => navigate(`/experiments/${experiment.id}`))
      .catch(error => {
        if (error instanceof ImportCsvError) {
          setErrors(error.errors);
        } else {
          setErrors([(error as Error).message]);
        }
      })
      .finally(() => setBusy(false));
  };

  return (
    <section>
      <header className="page-header">
        <div>
          <div className="eyebrow">IMPORT</div>
          <h1>Импорт эксперимента</h1>
          <p>
            Загрузите experiment package или уже рассчитанный <code>summary.csv</code>,
            чтобы посмотреть графики и таблицы без повторного запуска Monte-Carlo моделирования.
          </p>
        </div>
      </header>

      <div className="tabs">
        <button className={mode === "package" ? "active" : ""} onClick={() => { setMode("package"); setFile(null); setErrors([]); }}>
          Experiment package (.zip / .waveexp)
        </button>
        <button className={mode === "csv" ? "active" : ""} onClick={() => { setMode("csv"); setFile(null); setErrors([]); }}>
          Summary CSV (.csv)
        </button>
      </div>

      <div className="panel" style={{ maxWidth: 640 }}>
        <div className="form-grid">
          <label>
            {mode === "package" ? "Файл experiment package" : "Файл summary.csv"}
            <input
              key={mode}
              type="file"
              accept={mode === "package" ? ".zip,.waveexp,application/zip" : ".csv,text/csv"}
              onChange={event => setFile(event.target.files?.[0] || null)}
            />
          </label>
          <label>
            Название эксперимента
            <input
              type="text"
              placeholder={mode === "package" ? "(по умолчанию — имя из manifest)" : "(по умолчанию — имя файла)"}
              value={name}
              onChange={event => setName(event.target.value)}
            />
          </label>
          <label>
            Описание
            <textarea
              value={description}
              onChange={event => setDescription(event.target.value)}
              rows={3}
            />
          </label>
        </div>

        {errors.length > 0 && (
          <div className="alert error">
            <strong>Import failed</strong>
            <ul>
              {errors.map((error, index) => <li key={index}>{error}</li>)}
            </ul>
          </div>
        )}

        <button className="button primary" disabled={busy || !file} onClick={submit}>
          {busy ? "Импортируется..." : "Импортировать"}
        </button>

        <p className="muted" style={{ marginTop: 12 }}>
          Импорт не запускает вычисления: файл только проверяется (schema и
          согласованность метрик) и сохраняется как отдельный эксперимент с
          источником «Импортирован». Package — предпочтительный формат: он
          содержит runtime configuration и metadata в дополнение к результатам.
        </p>
      </div>
    </section>
  );
}
