import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, ImportCsvError } from "../api";

export function ImportExperimentPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  const submit = () => {
    if (!file) {
      setErrors(["Выберите файл summary.csv"]);
      return;
    }
    const effectiveName = name.trim() || file.name.replace(/\.csv$/i, "");
    setBusy(true);
    setErrors([]);
    api.importCsv(file, effectiveName, description)
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
            Загрузите уже рассчитанный <code>summary.csv</code>, чтобы посмотреть
            графики и таблицы без повторного запуска Monte-Carlo моделирования.
          </p>
        </div>
      </header>

      <div className="panel" style={{ maxWidth: 640 }}>
        <div className="form-grid">
          <label>
            Файл summary.csv
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={event => setFile(event.target.files?.[0] || null)}
            />
          </label>
          <label>
            Название эксперимента
            <input
              type="text"
              placeholder="(по умолчанию — имя файла)"
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
          источником «Импортирован (CSV)».
        </p>
      </div>
    </section>
  );
}
