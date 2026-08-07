import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { Data } from "plotly.js";

import { api } from "../api";
import { normalizePlotly, PlotlyChart } from "../PlotlyChart";
import type { Experiment } from "../types";


const METRIC_LABELS: Record<string, string> = {
  frame_error_rate: "FER",
  ber: "BER",
  pessimistic_ber: "Пессимистический BER",
  ber_on_success: "BER успешных декодирований",
  failure_rate: "Доля отказов",
  miscorrection_rate: "Доля ошибочных решений",
  conditional_miscorrection_rate: "Ошибки среди успешных решений",
  average_decoding_time_ms: "Среднее время, мс",
  avg_time_ms: "Среднее время, мс",
  codeword_error_rate: "Ошибка кодового слова",
  ambiguous_rate: "Неоднозначные решения",
};

const metricLabel = (name: string) => (
  METRIC_LABELS[name]
  || name.replaceAll("_", " ").replace(/^./, letter => letter.toUpperCase())
);

const decoderLabel = (name: string) => ({
  syndrome: "Syndrome",
  chase: "Chase",
  hard_mld: "Hard MLD",
  soft_mld: "Soft MLD",
}[name] || name);

const codeLabel = (name: string) => {
  const dimensions = name.match(/(\d+)[_x](\d+)/);
  const size = dimensions ? ` ${dimensions[1]}×${dimensions[2]}` : "";
  if (name.startsWith("wavelet")) return `Wavelet${size}`;
  if (name.startsWith("bch_derived")) return `BCH-derived${size}`;
  if (name.startsWith("bch")) return `BCH${size}`;
  return name;
};


export function ExperimentPage() {
  const { id = "" } = useParams();
  const plotRef = useRef<{ el: HTMLElement } | null>(null);
  const logRef = useRef<HTMLPreElement | null>(null);
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [schema, setSchema] = useState<{
    numeric_metrics: string[];
    codes: string[];
    decoders: string[];
  } | null>(null);
  const [series, setSeries] = useState<
    Array<{ name: string; x: number[]; y: number[] }>
  >([]);
  const [metric, setMetric] = useState("frame_error_rate");
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [selectedDecoders, setSelectedDecoders] = useState<string[]>([]);
  const [plotType, setPlotType] = useState<"line" | "scatter" | "bar">("line");
  const [graphShown, setGraphShown] = useState(false);
  const [plotError, setPlotError] = useState("");
  const [logScale, setLogScale] = useState(true);
  const [zeroMode, setZeroMode] = useState("floor");
  const [tab, setTab] = useState<"process" | "plots" | "data">("process");
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    api.experiment(id).then(setExperiment);
    api.logs(id).then(data => setLogs(data.lines));
  }, [id]);

  useEffect(() => {
    if (!experiment || ["completed", "failed", "cancelled", "interrupted"].includes(experiment.status)) {
      return;
    }
    const refresh = () => api.logs(id).then(data => setLogs(data.lines));
    const timer = window.setInterval(refresh, 700);
    return () => window.clearInterval(timer);
  }, [experiment?.status, id]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  useEffect(() => {
    if (!id) return;
    const source = new EventSource(`/api/experiments/${id}/events`);
    source.onmessage = event => setExperiment(JSON.parse(event.data));
    return () => source.close();
  }, [id]);

  useEffect(() => {
    if (experiment?.status !== "completed") return;
    api.resultSchema(id).then(result => {
      setSchema(result);
      setSelectedCodes(result.codes);
      setSelectedDecoders(result.decoders);
    });
    api.resultData(id).then(data => setRows(data.rows));
    setTab(current => current === "process" ? "plots" : current);
  }, [experiment?.status, id]);

  const showGraph = () => {
    if (!schema || !schema.numeric_metrics.includes(metric)) return;
    setPlotError("");
    api.plot({
      experiment_ids: [id],
      codes: selectedCodes,
      decoders: selectedDecoders,
      metrics: [metric],
      zero_mode: zeroMode,
    }).then(data => {
      setSeries(data.series);
      setGraphShown(true);
    }).catch((error: Error) => {
      setGraphShown(false);
      setPlotError(error.message);
    });
  };

  const progress = useMemo(() => {
    if (!experiment?.progress_total) return 0;
    return Math.round(
      experiment.progress_completed / experiment.progress_total * 100,
    );
  }, [experiment]);

  const exportDataset = (format: "csv" | "json") => {
    fetch("/api/plots/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        experiment_ids: [id],
        codes: selectedCodes,
        decoders: selectedDecoders,
        metrics: [metric],
        zero_mode: zeroMode,
        format,
      }),
    })
      .then(response => response.blob())
      .then(blob => {
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `plot_dataset.${format}`;
        link.click();
        URL.revokeObjectURL(link.href);
      });
  };

  const exportImage = async (format: "png" | "svg") => {
    if (!plotRef.current) return;
    const Plotly = normalizePlotly(await import("plotly.js-dist-min"));
    await Plotly.downloadImage(plotRef.current.el, {
      format,
      filename: `${experiment?.name || "plot"}_${metric}`,
      width: 1200,
      height: 720,
    });
  };

  if (!experiment) return <div className="loading">Загрузка...</div>;

  const plotData: Data[] = series.map(item => {
    const parts = item.name.split(" / ");
    const code = parts.length >= 4 ? parts.at(-3) || item.name : item.name;
    const decoder = parts.length >= 4 ? parts.at(-2) || "" : "";
    return {
    x: item.x,
    y: item.y,
    type: plotType === "bar" ? "bar" : "scatter",
    mode: plotType === "line" ? "lines+markers" : "markers",
      name: `${codeLabel(code)} · ${decoderLabel(decoder)}`,
      hovertemplate: `%{x:.2f} dB<br>%{y:.4g}<extra>${codeLabel(code)} · ${decoderLabel(decoder)}</extra>`,
    };
  });

  return (
    <section>
      <div className="crumb">
        <Link to="/">Эксперименты</Link> / {experiment.name}
      </div>
      <header className="page-header">
        <div>
          <div className="eyebrow">RUN DETAIL</div>
          <h1>{experiment.name}</h1>
          <p>{experiment.description || "Без описания"}</p>
        </div>
        <span className={`status ${experiment.status}`}>{experiment.status}</span>
      </header>

      <div className="progress-card panel">
        <div className="progress-label">
          <strong>{progress}%</strong>
          <span>
            {experiment.progress_completed} / {experiment.progress_total} серий
          </span>
        </div>
        <div className="progress-track">
          <div style={{ width: `${progress}%` }} />
        </div>
        <div className="current">
          {String(experiment.progress.code || "Ожидание запуска")}
          {experiment.progress.decoder
            ? ` / ${String(experiment.progress.decoder)}`
            : ""}
        </div>
        <div className="compute-strip">
          <div><span>Код</span><strong>{String(experiment.progress.code || "-")}</strong></div>
          <div><span>Декодер</span><strong>{String(experiment.progress.decoder || "-")}</strong></div>
          <div><span>Eb/N0</span><strong>{experiment.progress.ebn0_db !== undefined ? `${String(experiment.progress.ebn0_db)} dB` : "-"}</strong></div>
          <div><span>Этап</span><strong>{String(experiment.progress.stage || experiment.status)}</strong></div>
        </div>
        {!["completed", "failed", "cancelled", "interrupted"].includes(experiment.status) && (
          <button className="button danger" onClick={() => api.cancel(id)}>Отменить вычисление</button>
        )}
      </div>

      {experiment.error_message && (
        <div className="alert error">{experiment.error_message}</div>
      )}

      <div className="tabs">
        <button
          className={tab === "process" ? "active" : ""}
          onClick={() => setTab("process")}
        >
          Вычисления и лог
        </button>
        <button
          className={tab === "plots" ? "active" : ""}
          onClick={() => setTab("plots")}
          disabled={experiment.status !== "completed"}
        >
          Графики
        </button>
        <button
          className={tab === "data" ? "active" : ""}
          onClick={() => setTab("data")}
        >
          Данные
        </button>
      </div>

      {tab === "process" && (
        <div className="panel process-panel">
          <div className="panel-heading">
            <div><h2>Ход вычислений</h2><p className="muted">stdout процесса обновляется автоматически</p></div>
            <button className="button" onClick={() => api.logs(id).then(data => setLogs(data.lines))}>Обновить сейчас</button>
          </div>
          <pre ref={logRef} className="debug-console full-console">{logs.join("\n") || "Процесс запускается..."}</pre>
        </div>
      )}

      {tab === "plots" && (
        <div className="plot-stack">
          <div className="panel plot-config-compact">
            <div className="plot-main-controls">
              <label>
                Показатель
                <select value={metric} onChange={event => setMetric(event.target.value)}>
                  {(schema?.numeric_metrics || []).map(item => (
                    <option key={item} value={item}>{metricLabel(item)}</option>
                  ))}
                </select>
              </label>
              <label>
                Вид
                <select value={plotType} onChange={event => setPlotType(event.target.value as typeof plotType)}>
                  <option value="line">Линии</option>
                  <option value="scatter">Точки</option>
                  <option value="bar">Столбцы</option>
                </select>
              </label>
              <label>
                Шкала Y
                <select value={logScale ? "log" : "linear"} onChange={event => setLogScale(event.target.value === "log")}>
                  <option value="log">Логарифмическая</option>
                  <option value="linear">Линейная</option>
                </select>
              </label>
              <label>
                Нулевые точки
                <select value={zeroMode} onChange={event => setZeroMode(event.target.value)}>
                  <option value="floor">Показать как 0.5/N</option>
                  <option value="hide">Скрыть</option>
                  <option value="epsilon">Заменить на epsilon</option>
                </select>
              </label>
              <button className="button primary show-plot" disabled={!selectedCodes.length || !selectedDecoders.length} onClick={showGraph}>
                Показать график
              </button>
            </div>
            <div className="series-filters">
              <div>
                <span className="filter-title">Коды</span>
                <div className="filter-chips">
                  {schema?.codes.map(code => (
                    <button
                      className={`filter-chip ${selectedCodes.includes(code) ? "selected" : ""}`}
                      key={code}
                      onClick={() => setSelectedCodes(current => current.includes(code) ? current.filter(item => item !== code) : [...current, code])}
                    >
                      {codeLabel(code)}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <span className="filter-title">Декодеры</span>
                <div className="filter-chips">
                  {schema?.decoders.map(decoder => (
                    <button
                      className={`filter-chip ${selectedDecoders.includes(decoder) ? "selected" : ""}`}
                      key={decoder}
                      onClick={() => setSelectedDecoders(current => current.includes(decoder) ? current.filter(item => item !== decoder) : [...current, decoder])}
                    >
                      {decoderLabel(decoder)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div className="panel chart-panel">
            <div className="chart-export">
              <div>
                <strong className="chart-heading">{metricLabel(metric)} от Eb/N0</strong>
                <span className="muted">{graphShown ? `${series.length} серий` : "Выберите серии и нажмите «Показать график»"}</span>
              </div>
              {graphShown && <div><button className="button" onClick={() => exportImage("png")}>PNG</button><button className="button" onClick={() => exportImage("svg")}>SVG</button><button className="button" onClick={() => exportDataset("csv")}>CSV</button><button className="button" onClick={() => exportDataset("json")}>JSON</button></div>}
            </div>
            {plotError && (
              <div className="alert error">
                Не удалось построить график: {plotError}
              </div>
            )}
            {graphShown ? (
              <PlotlyChart
                data={plotData}
                layout={{ autosize: true, height: 540, margin: { l: 75, r: 25, t: 35, b: 115 }, xaxis: { title: { text: "Eb/N0, dB" }, gridcolor: "#e6ebe6" }, yaxis: { title: { text: metricLabel(metric) }, type: logScale ? "log" : "linear", gridcolor: "#e6ebe6" }, legend: { orientation: "h", y: -0.22, x: 0, font: { size: 11 } }, paper_bgcolor: "#ffffff", plot_bgcolor: "#ffffff", barmode: "group" }}
                onReady={element => { plotRef.current = { el: element }; }}
              />
            ) : <div className="plot-placeholder">График появится здесь</div>}
          </div>
        </div>
      )}

      {tab === "data" && (
        <div className="panel table-wrap">
          <table>
            <thead>
              <tr>
                {Object.keys(rows[0] || {}).map(key => <th key={key}>{key}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index}>
                  {Object.values(row).map((value, cellIndex) => (
                    <td key={cellIndex}>{String(value ?? "")}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
