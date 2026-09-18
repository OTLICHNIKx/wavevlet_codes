import { useEffect, useMemo, useRef, useState } from "react";
import type { Data, Layout } from "plotly.js";

import { api } from "../api";
import { PlotlyChart } from "../PlotlyChart";
import type {
  McStatsFileItem,
  McStatsResponse,
  McStatsSeries,
} from "../types";

const LOG_METRICS = new Set([
  "ber",
  "frame_error_rate",
  "failure_rate",
  "miscorrection_rate",
  "conditional_miscorrection_rate",
  "ambiguous_rate",
]);

const METRIC_LABELS: Record<string, string> = {
  ber: "BER",
  frame_error_rate: "FER",
  failure_rate: "failure rate",
  miscorrection_rate: "miscorrection rate",
  conditional_miscorrection_rate: "cond. miscorrection",
  ambiguous_rate: "ambiguous rate",
  average_decoding_time_ms: "decode time, ms",
};

const METRIC_ORDER = [
  "ber",
  "frame_error_rate",
  "failure_rate",
  "miscorrection_rate",
  "conditional_miscorrection_rate",
  "ambiguous_rate",
  "average_decoding_time_ms",
];

const DECODER_LABELS: Record<string, string> = {
  syndrome: "Syndrome",
  chase: "Chase",
  hard_mld: "Hard MLD",
  soft_mld: "Soft MLD",
};

const FAMILY_LABELS: Record<string, string> = {
  wavelet: "Wavelet",
  bch_derived: "BCH-derived",
  goppa_derived: "Goppa-derived",
  reed_solomon_binary: "RS binary",
  ldpc: "LDPC",
};

const SIZES = ["16_8", "32_16", "64_32"] as const;
const SIZE_LABELS: Record<string, string> = {
  "16_8": "16/8",
  "32_16": "32/16",
  "64_32": "64/32",
};

function splitCode(code: string): { family: string; size: string } {
  const suffix = SIZES.find(size => code.endsWith(`_${size}`));
  if (!suffix) return { family: code, size: "" };
  return { family: code.slice(0, code.length - suffix.length - 1), size: suffix };
}

export function McStatsPage() {
  const [items, setItems] = useState<McStatsFileItem[]>([]);
  const [file, setFile] = useState("");
  const [channel, setChannel] = useState("");
  const [metric, setMetric] = useState("");
  const [enabledDecoders, setEnabledDecoders] = useState<string[] | null>(null);
  const [enabledCodes, setEnabledCodes] = useState<string[] | null>(null);
  const [data, setData] = useState<McStatsResponse | null>(null);
  const [error, setError] = useState("");
  const [uploadName, setUploadName] = useState("");
  const [uploadBusy, setUploadBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement | null>(null);

  const refreshFiles = () => api.mcFiles().then(result => {
    setItems(result.items);
    setFile(current =>
      (current && result.items.some(item => item.name === current))
        ? current
        : (result.items[0]?.name || ""),
    );
    return result;
  });

  useEffect(() => {
    refreshFiles().catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!file) return;
    api.mcSeries({
      file,
      channel: channel || undefined,
      metric: metric || undefined,
    }).then(result => {
      setData(result);
      setError("");
      if (!channel && result.selected.channel) setChannel(result.selected.channel);
      if (!metric && result.selected.metric) setMetric(result.selected.metric);
    }).catch((err: Error) => setError(err.message));
  }, [file, channel, metric]);

  const universe = data?.universe;
  const allDecoders = universe?.decoders ?? [];
  const allCodes = universe?.codes ?? [];
  const shownDecoders = useMemo(
    () => enabledDecoders ?? allDecoders,
    [enabledDecoders, allDecoders],
  );
  const shownCodes = useMemo(
    () => enabledCodes ?? allCodes,
    [enabledCodes, allCodes],
  );

  const families = useMemo(() => {
    const order = Object.keys(FAMILY_LABELS);
    const byFamily = new Map<string, string[]>();
    allCodes.forEach(code => {
      const { family, size } = splitCode(code);
      const list = byFamily.get(family) ?? [];
      if (size) list.push(size);
      byFamily.set(family, list);
    });
    return [...byFamily.entries()].sort(
      (a, b) => order.indexOf(a[0]) - order.indexOf(b[0]),
    );
  }, [allCodes]);

  const toggleIn = (
    setter: typeof setEnabledDecoders,
    all: string[],
    current: string[],
    value: string,
  ) => {
    setter(
      current.includes(value)
        ? all.filter(item => item !== value && current.includes(item))
        : all.filter(item => current.includes(item) || item === value),
    );
  };

  const toggleDecoder = (decoder: string) =>
    toggleIn(setEnabledDecoders, allDecoders, shownDecoders, decoder);

  const toggleCode = (code: string) =>
    toggleIn(setEnabledCodes, allCodes, shownCodes, code);

  const toggleFamily = (family: string) => {
    const codesOfFamily = allCodes.filter(
      code => splitCode(code).family === family,
    );
    const allOn = codesOfFamily.every(code => shownCodes.includes(code));
    setEnabledCodes(
      allOn
        ? shownCodes.filter(code => !codesOfFamily.includes(code))
        : allCodes.filter(
          code => codesOfFamily.includes(code) || shownCodes.includes(code),
        ),
    );
  };

  const upload = async (selected: File | undefined) => {
    if (!selected) return;
    setUploadBusy(true);
    setError("");
    try {
      const result = await api.mcUpload(selected, uploadName || selected.name);
      await refreshFiles();
      setFile(result.name);
      setUploadName("");
      if (fileInput.current) fileInput.current.value = "";
    } catch (err) {
      setError(`Загрузка не удалась: ${(err as Error).message}`);
    } finally {
      setUploadBusy(false);
    }
  };

  const removeCurrent = async () => {
    if (!file) return;
    const item = items.find(entry => entry.name === file);
    if (!item || item.source !== "uploaded") return;
    if (!window.confirm(`Удалить загруженный файл ${item.name}?`)) return;
    try {
      await api.mcDelete(item.name);
      setFile("");
      setData(null);
      const result = await refreshFiles();
      if (!result.items.length) setError("CSV Монте-Карло статистики не найдены");
    } catch (err) {
      setError(`Удаление не удалось: ${(err as Error).message}`);
    }
  };

  const currentItem = items.find(entry => entry.name === file);

  const plotData = useMemo<Data[]>(() => {
    const series: McStatsSeries[] = (data?.series ?? []).filter(
      item => shownDecoders.includes(item.decoder)
        && shownCodes.includes(item.code),
    );
    const traces: Data[] = [];
    series.forEach(item => {
      const { family, size } = splitCode(item.code);
      const label = `${FAMILY_LABELS[family] ?? family}${size ? ` ${SIZE_LABELS[size] ?? size}` : ""} · ${DECODER_LABELS[item.decoder] ?? item.decoder}`;
      traces.push({
        x: item.x,
        y: item.ci_low,
        type: "scatter",
        mode: "lines",
        line: { width: 0 },
        showlegend: false,
        hoverinfo: "skip",
        name: `${label} CI low`,
      });
      traces.push({
        x: item.x,
        y: item.ci_high,
        type: "scatter",
        mode: "lines",
        line: { width: 0 },
        fill: "tonexty",
        fillcolor: "rgba(90, 130, 200, 0.14)",
        showlegend: false,
        hoverinfo: "skip",
        name: `${label} 95% CI`,
      });
      traces.push({
        x: item.x,
        y: item.y,
        type: "scatter",
        mode: "lines+markers",
        name: label,
        hovertemplate: `%{x:.1f} dB<br>%{y:.4g}<extra>${label}</extra>`,
      });
    });
    return traces;
  }, [data, shownCodes, shownDecoders]);

  const orderedMetrics = useMemo(() => {
    if (!universe) return [];
    return METRIC_ORDER.filter(m => universe.metrics.includes(m));
  }, [universe]);

  const logY = LOG_METRICS.has(metric || data?.selected.metric || "");

  const layout = useMemo<Partial<Layout>>(() => ({
    autosize: true,
    height: 560,
    margin: { l: 75, r: 25, t: 45, b: 90 },
    title: data
      ? {
        text: `${data.selected.channel ?? ""} · ` +
          `${METRIC_LABELS[data.selected.metric ?? ""] ?? data.selected.metric} — ` +
          `среднее по ${data.series[0]?.seeds ?? "?"} seed × ${data.series[0]?.words ?? "?"} слов`,
      }
      : undefined,
    xaxis: { title: { text: "Eb/N0, dB" }, gridcolor: "#e6ebe6" },
    yaxis: {
      title: { text: METRIC_LABELS[data?.selected.metric ?? ""] ?? "значение" },
      type: logY ? "log" : "linear",
      gridcolor: "#e6ebe6",
    },
    legend: { orientation: "h", y: -0.18, font: { size: 11 } },
    showlegend: true,
  }), [data, logY]);

  return <section className="panel">
    <div className="panel-heading">
      <h2>Монте-Карло статистика (усреднение по seed)</h2>
    </div>
    {error && <div className="alert">{error}</div>}
    {!error && !items.length && (
      <div className="alert">
        CSV статистики не найдены. Запустите
        research/run_wavelet_channel_decoder_experiment.py
        или загрузите all-metrics CSV ниже.
      </div>
    )}
    <div className="panel-heading" style={{ marginTop: 8 }}>
      <h3>Загрузка эксперимента</h3>
    </div>
    <div className="two-col">
      <label>
        Имя (необязательно)
        <input
          type="text"
          value={uploadName}
          placeholder="wavelet_mc_5seed"
          onChange={event => setUploadName(event.target.value)}
        />
      </label>
      <label>
        CSV-файл статистики
        <input
          ref={fileInput}
          type="file"
          accept=".csv,text/csv"
          disabled={uploadBusy}
          onChange={event => void upload(event.target.files?.[0])}
        />
      </label>
    </div>
    {uploadBusy && <div className="alert">Загрузка…</div>}

    {items.length > 0 && (
      <>
        <div className="two-col">
          <label>
            Файл статистики
            <select value={file} onChange={event => {
              setFile(event.target.value);
              setData(null);
            }}>
              {items.map(item => (
                <option key={`${item.source}:${item.name}`} value={item.name}>
                  {item.source === "uploaded" ? "⬆ загружен · " : "results · "}
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <div>
            {currentItem?.source === "uploaded" && (
              <button type="button" className="button" onClick={() => void removeCurrent()}>
                Удалить загруженный файл
              </button>
            )}
          </div>
          <label>
            Канал
            <select value={channel} onChange={event => setChannel(event.target.value)}>
              {(universe?.channels ?? []).map(name => <option key={name} value={name}>{name}</option>)}
            </select>
          </label>
          <label>
            Метрика
            <select value={metric} onChange={event => setMetric(event.target.value)}>
              {orderedMetrics.map(name => (
                <option key={name} value={name}>{METRIC_LABELS[name] ?? name}</option>
              ))}
            </select>
          </label>
        </div>

        <div style={{ display: "grid", gap: 8, margin: "6px 0 16px" }}>
          <span><strong>Семейства кодов</strong> (снятие галочки скрывает кривые и CI)</span>
          {families.map(([family, sizes]) => (
            <div key={family} style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
              <label className="check">
                <input
                  type="checkbox"
                  checked={sizes.every(size =>
                    shownCodes.includes(`${family}_${size}`),
                  )}
                  onChange={() => toggleFamily(family)}
                />
                <strong>{FAMILY_LABELS[family] ?? family}</strong>
              </label>
              {sizes.map(size => (
                <label key={size} className="check">
                  <input
                    type="checkbox"
                    checked={shownCodes.includes(`${family}_${size}`)}
                    onChange={() => toggleCode(`${family}_${size}`)}
                  />
                  {SIZE_LABELS[size] ?? size}
                </label>
              ))}
            </div>
          ))}
          <span style={{ marginTop: 6 }}><strong>Декодеры</strong></span>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
            {allDecoders.map(decoder => (
              <label key={decoder} className="check">
                <input
                  type="checkbox"
                  checked={shownDecoders.includes(decoder)}
                  onChange={() => toggleDecoder(decoder)}
                />
                {DECODER_LABELS[decoder] ?? decoder}
              </label>
            ))}
          </div>
        </div>

        {plotData.length > 0
          ? <PlotlyChart data={plotData} layout={layout} />
          : <div className="alert">
            {shownCodes.length && shownDecoders.length
              ? "Нет данных для выбранной комбинации"
              : "Всё скрыто — включите хотя бы одно семейство и один декодер"}
          </div>}
      </>
    )}
  </section>;
}
