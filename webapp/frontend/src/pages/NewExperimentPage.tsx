import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { CodeConfigEditor } from "../CodeConfigEditor";
import { EbN0Editor } from "../EbN0Editor";
import type { CodeConfig, CustomPreset, Experiment, ExperimentPreview, ResearchConfig } from "../types";


const emptyConfig: ResearchConfig = {
  message_count: 50,
  message_seed: 12345,
  noise_seed: 54321,
  ebn0_db_values: [2],
  results_dir: "",
  codes: [],
  decoders: {
    run_syndrome: true,
    run_hard_mld: false,
    run_soft_mld: false,
    run_chase: true,
    syndrome_max_error_weight: 2,
    chase_inner_decoder_max_error_weight: 2,
    chase_unreliable_positions_count: 4,
    max_k_for_mld: 16,
  },
};


export function NewExperimentPage() {
  const navigate = useNavigate();
  const [builtinPresets, setBuiltinPresets] = useState<
    Array<{ id: string; name: string; config: ResearchConfig }>
  >([]);
  const [customPresets, setCustomPresets] = useState<CustomPreset[]>([]);
  const [codePresets, setCodePresets] = useState<
    Array<{ id: string; name: string; config: CodeConfig }>
  >([]);
  const [selected, setSelected] = useState("");
  const [selectedCode, setSelectedCode] = useState("");
  const [config, setConfig] = useState(emptyConfig);
  const [name, setName] = useState("web experiment");
  const [description, setDescription] = useState("");
  const [step, setStep] = useState(1);
  const [report, setReport] = useState<{
    valid: boolean;
    errors: string[];
    warnings: string[];
    report: Record<string, number>;
  } | null>(null);
  const [preview, setPreview] = useState<ExperimentPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [launched, setLaunched] = useState<Experiment | null>(null);
  const [launchLogs, setLaunchLogs] = useState<string[]>([]);
  const [presetMessage, setPresetMessage] = useState("");

  useEffect(() => {
    api.presets().then(data => {
      setBuiltinPresets(data.experiments);
      setCustomPresets(data.user);
      setCodePresets(data.codes);
      if (data.experiments[0]) {
        setSelected(data.experiments[0].id);
        setConfig(data.experiments[0].config);
      }
      if (data.codes[0]) setSelectedCode(data.codes[0].id);
    });
  }, []);

  useEffect(() => {
    if (!launched) return;
    const source = new EventSource(`/api/experiments/${launched.id}/events`);
    source.onmessage = event => setLaunched(JSON.parse(event.data));
    const refreshLogs = () => api.logs(launched.id).then(data => setLaunchLogs(data.lines));
    refreshLogs();
    const timer = window.setInterval(refreshLogs, 800);
    return () => {
      source.close();
      window.clearInterval(timer);
    };
  }, [launched?.id]);

  const update = (patch: Partial<ResearchConfig>) => {
    setConfig(current => ({ ...current, ...patch }));
    setPreview(null);
  };
  const loadPreset = (id: string) => {
    const preset = [...builtinPresets, ...customPresets].find(item => item.id === id);
    if (preset) {
      setConfig(structuredClone(preset.config));
      setName(preset.name);
      setDescription(
        "description" in preset && typeof preset.description === "string"
          ? preset.description
          : "",
      );
    }
    setSelected(id);
    setPreview(null);
  };
  const selectedCustomPreset = customPresets.find(item => item.id === selected);
  const savePreset = async () => {
    setBusy(true);
    try {
      const preset = selectedCustomPreset
        ? await api.updatePreset(selectedCustomPreset.id, name, description, config)
        : await api.createPreset(name, description, config);
      setCustomPresets(current => [preset, ...current.filter(item => item.id !== preset.id)]);
      setSelected(preset.id);
    } catch (error) {
      setReport({ valid: false, errors: [(error as Error).message], warnings: [], report: {} });
    } finally {
      setBusy(false);
    }
  };
  const duplicatePreset = async () => {
    if (!selectedCustomPreset) return;
    const preset = await api.duplicatePreset(selectedCustomPreset.id);
    setCustomPresets(current => [preset, ...current]);
    setSelected(preset.id);
    setName(preset.name);
    setDescription(preset.description);
    setConfig(structuredClone(preset.config));
  };
  const deletePreset = async () => {
    if (!selectedCustomPreset || !window.confirm(`Удалить пресет «${selectedCustomPreset.name}»?`)) return;
    await api.deletePreset(selectedCustomPreset.id);
    setCustomPresets(current => current.filter(item => item.id !== selectedCustomPreset.id));
    setSelected("");
  };
  const importPreset = async (file: File) => {
    setBusy(true);
    setPresetMessage("");
    try {
      const preset = await api.importPreset(file);
      setCustomPresets(current => [preset, ...current]);
      setSelected(preset.id);
      setName(preset.name);
      setDescription(preset.description);
      setConfig(structuredClone(preset.config));
      setPreview(null);
      setPresetMessage("Preset импортирован. Эксперимент не запущен.");
    } catch (error) {
      setReport({ valid: false, errors: [(error as Error).message], warnings: [], report: {} });
    } finally {
      setBusy(false);
    }
  };
  const addCode = () => {
    const preset = codePresets.find(item => item.id === selectedCode);
    if (!preset) return;
    const code = structuredClone(preset.config);
    if (config.codes.some(item => item.name === code.name)) {
      code.name = `${code.name}_${config.codes.length + 1}`;
    }
    update({ codes: [...config.codes, code] });
  };
  const editCode = (index: number, patch: Partial<CodeConfig>) => {
    update({
      codes: config.codes.map((code, current) => (
        current === index ? { ...code, ...patch } : code
      )),
    });
  };
  const buildPreview = () => api.preview(config)
    .then(result => {
      setPreview(result);
      setReport({
        valid: result.valid,
        errors: result.errors,
        warnings: result.warnings,
        report: Object.fromEntries(
          Object.entries(result.workload).filter(([, value]) => typeof value === "number"),
        ) as Record<string, number>,
      });
    })
    .catch((error: Error) => {
      setPreview(null);
      setReport({ valid: false, errors: [error.message], warnings: [], report: {} });
    });
  const create = async () => {
    setBusy(true);
    try {
      const experiment = await api.create(name, description, config);
      setLaunched(experiment);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <header className="page-header">
        <div>
          <div className="eyebrow">CONFIGURE / RUN</div>
          <h1>Новый эксперимент</h1>
          <p>Настройте серию, проверьте матрицы и запустите subprocess.</p>
        </div>
      </header>

      <div className="steps">
        {["Общие параметры", "Коды", "Декодеры", "Проверка", "Запуск"].map(
          (label, index) => (
            <button
              key={label}
              className={step === index + 1 ? "active" : ""}
              onClick={() => setStep(index + 1)}
            >
              <b>0{index + 1}</b>{label}
            </button>
          ),
        )}
      </div>

      <div className="form-grid">
        <div className="panel">
          {step === 1 && (
            <>
              <h2>Общие параметры</h2>
              <label>
                Пресет эксперимента
                <select value={selected} onChange={event => loadPreset(event.target.value)}>
                  <option value="">Выбрать</option>
                  <optgroup label="Built-in presets">
                    {builtinPresets.map(preset => (
                      <option value={preset.id} key={preset.id}>{preset.name}</option>
                    ))}
                  </optgroup>
                  <optgroup label="Custom presets">
                    {customPresets.map(preset => (
                      <option value={preset.id} key={preset.id}>{preset.name}</option>
                    ))}
                  </optgroup>
                </select>
              </label>
              <label>
                Название
                <input value={name} onChange={event => setName(event.target.value)} />
              </label>
              <div className="preset-actions">
                <button
                  className="button"
                  onClick={() => {
                    setSelected("");
                    setName("Новый custom preset");
                    setDescription("");
                  }}
                >
                  Новый custom preset
                </button>
                <button className="button primary" disabled={busy || !name.trim()} onClick={savePreset}>
                  {selectedCustomPreset ? "Сохранить изменения" : "Save preset"}
                </button>
                {selectedCustomPreset && (
                  <>
                    <button className="button" onClick={duplicatePreset}>Duplicate</button>
                    <button className="button" onClick={() => api.exportPreset(selectedCustomPreset.id, selectedCustomPreset.name)}>Export JSON</button>
                    <button className="button danger" onClick={deletePreset}>Delete</button>
                  </>
                )}
                <label className="button preset-file-button">
                  Import JSON
                  <input
                    type="file"
                    accept=".json,application/json"
                    onChange={event => {
                      const file = event.target.files?.[0];
                      if (file) void importPreset(file);
                      event.target.value = "";
                    }}
                  />
                </label>
              </div>
              {presetMessage && <div className="alert">{presetMessage}</div>}
              <label>
                Описание
                <textarea value={description} onChange={event => setDescription(event.target.value)} />
              </label>
              <div className="two-col">
                <label>
                  Сообщений
                  <input type="number" value={config.message_count} onChange={event => update({ message_count: Number(event.target.value) })} />
                </label>
                <label>
                  Seed сообщений
                  <input type="number" value={config.message_seed} onChange={event => update({ message_seed: Number(event.target.value) })} />
                </label>
                <label>
                  Seed шума
                  <input type="number" value={config.noise_seed} onChange={event => update({ noise_seed: Number(event.target.value) })} />
                </label>
                <div className="span-two">
                  <EbN0Editor
                    values={config.ebn0_db_values}
                    onChange={ebn0_db_values => update({ ebn0_db_values })}
                  />
                </div>
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <div className="panel-heading">
                <h2>Коды</h2>
                <div className="add-code">
                  <select value={selectedCode} onChange={event => setSelectedCode(event.target.value)}>
                    {codePresets.map(preset => (
                      <option value={preset.id} key={preset.id}>{preset.name}</option>
                    ))}
                  </select>
                  <button className="button primary" onClick={addCode}>Добавить</button>
                </div>
              </div>
              {config.codes.map((code, index) => (
                <div className="code-card" key={`${index}-${code.name}`}>
                  <div className="code-row">
                    <div>
                      <strong>{code.name}</strong>
                      <span>
                        {code.family} / [{code.n}, {code.k}] / R={(code.k / code.n).toFixed(3)}
                      </span>
                    </div>
                    <div>
                      <button
                        className="button"
                        onClick={() => update({
                          codes: [
                            ...config.codes,
                            { ...structuredClone(code), name: `${code.name}_copy` },
                          ],
                        })}
                      >
                        Клонировать
                      </button>
                      <button
                        className="button"
                        onClick={() => update({
                          codes: config.codes.filter((_, current) => current !== index),
                        })}
                      >
                        Удалить
                      </button>
                    </div>
                  </div>
                  <div className="three-col">
                    <label>
                      Имя
                      <input value={code.name} onChange={event => editCode(index, { name: event.target.value })} />
                    </label>
                    <label>
                      Семейство
                      <select
                        value={code.family}
                        onChange={event => editCode(index, {
                          family: event.target.value as CodeConfig["family"],
                        })}
                      >
                        <option value="wavelet">wavelet</option>
                        <option value="bch">bch</option>
                        <option value="bch_derived">bch_derived</option>
                        <option value="goppa_derived">goppa_derived</option>
                        <option value="reed_solomon_binary">reed_solomon_binary</option>
                      </select>
                    </label>
                    <label>
                      n / k
                      <div className="inline-inputs">
                        <input type="number" value={code.n} onChange={event => editCode(index, { n: Number(event.target.value) })} />
                        <input type="number" value={code.k} onChange={event => editCode(index, { k: Number(event.target.value) })} />
                      </div>
                    </label>
                  </div>
                  <CodeConfigEditor
                    code={code}
                    onChange={patch => editCode(index, patch)}
                  />
                </div>
              ))}
            </>
          )}

          {step === 3 && (
            <>
              <h2>Декодеры</h2>
              {(["run_syndrome", "run_chase", "run_hard_mld", "run_soft_mld"] as const).map(key => (
                <label className="check" key={key}>
                  <input
                    type="checkbox"
                    checked={config.decoders[key]}
                    onChange={event => update({
                      decoders: { ...config.decoders, [key]: event.target.checked },
                    })}
                  />
                  {key.replace("run_", "")}
                </label>
              ))}
              <div className="two-col">
                <label>
                  Syndrome t
                  <input type="number" value={config.decoders.syndrome_max_error_weight} onChange={event => update({ decoders: { ...config.decoders, syndrome_max_error_weight: Number(event.target.value) } })} />
                </label>
                <label>
                  Chase t
                  <input type="number" value={config.decoders.chase_inner_decoder_max_error_weight} onChange={event => update({ decoders: { ...config.decoders, chase_inner_decoder_max_error_weight: Number(event.target.value) } })} />
                </label>
                <label>
                  Chase p
                  <input type="number" value={config.decoders.chase_unreliable_positions_count} onChange={event => update({ decoders: { ...config.decoders, chase_unreliable_positions_count: Number(event.target.value) } })} />
                </label>
                <label>
                  Max k для MLD
                  <input
                    type="number"
                    min={1}
                    value={config.decoders.max_k_for_mld}
                    onChange={event => update({
                      decoders: {
                        ...config.decoders,
                        max_k_for_mld: Number(event.target.value),
                      },
                    })}
                  />
                </label>
              </div>
              <div className="cost-note">
                Chase p={config.decoders.chase_unreliable_positions_count}: {2 ** config.decoders.chase_unreliable_positions_count} шаблонов.
              </div>
            </>
          )}

          {step === 4 && (
            <>
              <h2>Проверка</h2>
              <button className="button primary" onClick={buildPreview}>
                Preview experiment
              </button>
              {report && (
                <div className={`validation ${report.valid ? "valid" : "invalid"}`}>
                  <strong>{report.valid ? "Конфигурация корректна" : "Есть ошибки"}</strong>
                  {report.errors.map(error => <div key={error}>{error}</div>)}
                  {report.warnings.map(warning => <div className="warning" key={warning}>{warning}</div>)}
                  {Object.entries(report.report).map(([key, value]) => (
                    <span className="metric" key={key}>{key}: {value}</span>
                  ))}
                </div>
              )}
              {preview?.valid && preview.summary && (
                <div className="preview-stack">
                  <div className="preview-summary">
                    <div><span>Messages</span><strong>{preview.summary.message_count.toLocaleString("ru-RU")}</strong></div>
                    <div><span>Codes</span><strong>{preview.summary.code_count}</strong></div>
                    <div><span>Eb/N0 points</span><strong>{preview.summary.ebn0_db_values.length}</strong></div>
                    <div><span>Workload</span><strong>{String(preview.workload.level).toUpperCase()}</strong></div>
                  </div>
                  <div className="crn-report">
                    <strong>Common random numbers: {preview.common_random_numbers.enabled ? "ON" : "OFF"}</strong>
                    <span>{preview.common_random_numbers.same_information_messages ? "✓" : "×"} same information messages</span>
                    <span>{preview.common_random_numbers.same_base_noise ? "✓" : "×"} same base noise {preview.common_random_numbers.scope}</span>
                  </div>
                  {preview.groups.map(group => (
                    <div className="preview-group" key={group.key}>
                      <div className="panel-heading">
                        <h3>{group.key}</h3>
                        <div>
                          <span className={`preview-check ${group.rate_matched ? "ok" : "warn"}`}>Rate {group.rate_matched ? "matched" : "mismatch"}</span>
                          <span className={`preview-check ${group.decoder_matched ? "ok" : "warn"}`}>Decoder {group.decoder_matched ? "matched" : "mismatch"}</span>
                        </div>
                      </div>
                      <div className="preview-code-grid">
                        {group.codes.map(code => (
                          <div key={code.name}>
                            <strong>{code.name}</strong>
                            <span>{code.family} · [{code.n},{code.k}] · R={code.rate.toFixed(3)}</span>
                            <span>Syndrome t={code.syndrome_t} · Chase t={code.chase_inner_t}, p={code.chase_p}</span>
                            <span>Hard MLD: {code.hard_mld.status}{code.hard_mld.reason ? ` (${code.hard_mld.reason})` : ""}</span>
                            <span>Soft MLD: {code.soft_mld.status}{code.soft_mld.reason ? ` (${code.soft_mld.reason})` : ""}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                  <div className="workload-details">
                    <span>Code/SNR points: <strong>{preview.workload.code_snr_points}</strong></span>
                    <span>Maximum decoder evaluations: <strong>{preview.workload.maximum_decoder_evaluations}</strong></span>
                    <span>Total frames: <strong>{preview.workload.total_frames}</strong></span>
                  </div>
                </div>
              )}
            </>
          )}

          {step === 5 && (
            <>
              <h2>Запуск</h2>
              <p>Конфигурация будет сохранена как runtime JSON, а исследование пойдёт отдельным процессом.</p>
              <button
                className="button primary"
                disabled={busy || !config.codes.length || !preview?.valid}
                onClick={create}
              >
                {busy ? "Создание..." : preview?.valid ? "Запустить эксперимент" : "Сначала выполните Preview"}
              </button>
            </>
          )}

          <div className="form-actions">
            {step > 1 && <button className="button" onClick={() => setStep(step - 1)}>Назад</button>}
            {step < 5 && <button className="button primary" onClick={() => setStep(step + 1)}>Далее</button>}
          </div>
        </div>

        <aside className="summary panel">
          <div className="eyebrow">LIVE SUMMARY</div>
          <h2>{config.codes.length} кодов</h2>
          <p>{config.message_count} сообщений</p>
          <p>{config.ebn0_db_values.length} точек Eb/N0</p>
          <p>{Object.values(config.decoders).filter(value => value === true).length} активных декодеров</p>
        </aside>
      </div>

      {launched && (
        <div className="modal-backdrop">
          <div className="run-modal">
            <div className="panel-heading">
              <div>
                <div className="eyebrow">EXPERIMENT PROCESS</div>
                <h2>{launched.name}</h2>
              </div>
              <span className={`status ${launched.status}`}>{launched.status}</span>
            </div>
            <div className="run-modal-progress">
              <div className="progress-label">
                <strong>
                  {launched.progress_total
                    ? Math.round(launched.progress_completed / launched.progress_total * 100)
                    : 0}%
                </strong>
                <span>{launched.progress_completed} / {launched.progress_total} серий</span>
              </div>
              <div className="progress-track">
                <div style={{
                  width: `${launched.progress_total
                    ? launched.progress_completed / launched.progress_total * 100
                    : 0}%`,
                }} />
              </div>
              <div className="current">
                Код: {String(launched.progress.code || "подготовка")}
                {launched.progress.decoder
                  ? ` / декодер: ${String(launched.progress.decoder)}`
                  : ""}
                {launched.progress.ebn0_db !== undefined
                  ? ` / Eb/N0: ${String(launched.progress.ebn0_db)} dB`
                  : ""}
              </div>
            </div>
            <pre className="debug-console">
              {launchLogs.join("\n") || "Процесс запускается..."}
            </pre>
            <div className="modal-actions">
              {!["completed", "failed", "cancelled", "interrupted"].includes(launched.status) && (
                <button className="button" onClick={() => api.cancel(launched.id)}>
                  Отменить
                </button>
              )}
              <button
                className="button primary"
                onClick={() => navigate(`/experiments/${launched.id}`)}
              >
                {launched.status === "completed" ? "Открыть графики" : "Открыть вычисления"}
              </button>
              <button className="button" onClick={() => setLaunched(null)}>Закрыть окно</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
