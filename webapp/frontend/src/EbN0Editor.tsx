import { useEffect, useState } from "react";


type Props = {
  values: number[];
  onChange: (values: number[]) => void;
};


type Mode = "explicit" | "range";


function buildRange(start: number, stop: number, step: number): number[] {
  if (!Number.isFinite(start) || !Number.isFinite(stop) || !Number.isFinite(step)) {
    return [];
  }
  if (step <= 0 || stop < start) return [];

  const values: number[] = [];
  const epsilon = Math.abs(step) * 1e-9 + 1e-12;
  for (let value = start; value <= stop + epsilon; value += step) {
    values.push(Number(value.toFixed(12)));
    if (values.length > 10000) break;
  }
  return values;
}


export function EbN0Editor({ values, onChange }: Props) {
  const [mode, setMode] = useState<Mode>("explicit");
  const [start, setStart] = useState(values[0] ?? 0);
  const [stop, setStop] = useState(values.at(-1) ?? 5);
  const [step, setStep] = useState(0.5);
  const [explicit, setExplicit] = useState(values.join(", "));

  useEffect(() => {
    setExplicit(values.join(", "));
  }, [values]);

  const applyRange = (nextStart = start, nextStop = stop, nextStep = step) => {
    const generated = buildRange(nextStart, nextStop, nextStep);
    if (generated.length) onChange(generated);
  };

  return (
    <div className="ebn0-editor">
      <div className="mode-switch">
        <button
          type="button"
          className={`button ${mode === "explicit" ? "selected" : ""}`}
          onClick={() => setMode("explicit")}
        >
          Явный список
        </button>
        <button
          type="button"
          className={`button ${mode === "range" ? "selected" : ""}`}
          onClick={() => setMode("range")}
        >
          Диапазон
        </button>
      </div>

      {mode === "explicit" ? (
        <label>
          Eb/N0, dB
          <input
            value={explicit}
            onChange={event => setExplicit(event.target.value)}
            onBlur={() => {
              const parsed = explicit
                .split(/[\s,;]+/)
                .filter(Boolean)
                .map(Number)
                .filter(Number.isFinite);
              if (parsed.length) onChange(parsed);
            }}
            placeholder="0, 0.5, 1, 1.5, ..."
          />
        </label>
      ) : (
        <div className="three-col">
          <label>
            От
            <input
              type="number"
              step="any"
              value={start}
              onChange={event => {
                const value = Number(event.target.value);
                setStart(value);
                applyRange(value, stop, step);
              }}
            />
          </label>
          <label>
            До
            <input
              type="number"
              step="any"
              value={stop}
              onChange={event => {
                const value = Number(event.target.value);
                setStop(value);
                applyRange(start, value, step);
              }}
            />
          </label>
          <label>
            Шаг
            <input
              type="number"
              min="0.000001"
              step="any"
              value={step}
              onChange={event => {
                const value = Number(event.target.value);
                setStep(value);
                applyRange(start, stop, value);
              }}
            />
          </label>
        </div>
      )}

      <div className="field-hint">
        Итоговые точки ({values.length}): {values.join(", ")}
      </div>
    </div>
  );
}
