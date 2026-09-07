import type { CodeConfig } from "./types";


type Props = {
  code: CodeConfig;
  onChange: (patch: Partial<CodeConfig>) => void;
};


function optionalNumber(value: string): number | null {
  if (value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}


function binaryVectorToText(values?: number[] | null): string {
  return values?.join(", ") ?? "";
}


function parseBinaryVector(text: string): number[] | null {
  const normalized = text.trim();
  if (!normalized) return null;

  const values = normalized
    .split(/[\s,;]+/)
    .filter(Boolean)
    .map(Number);

  if (values.some(value => value !== 0 && value !== 1)) {
    return null;
  }
  return values;
}



function integerVectorToText(values?: number[] | null): string {
  return values?.join(", ") ?? "";
}
function parseIntegerVector(text: string): number[] | null {
  const normalized = text.trim();
  if (!normalized) return null;
  const values = normalized.split(/[\s,;]+/).filter(Boolean).map(Number);
  return values.every(value => Number.isInteger(value) && value >= 0) ? values : null;
}
export function CodeConfigEditor({ code, onChange }: Props) {
  const grsTargetHint = code.n === 64 && code.k === 32
    ? "Target preset: GRS Binary [64,32,10], t = 3."
    : code.n === 32 && code.k === 16
      ? "Target preset: GRS Binary [32,16,6], t = 2."
      : "Target preset: GRS Binary [16,8,5], t = 2.";
  const hText = binaryVectorToText(code.h);
  const gText = binaryVectorToText(code.g);

  return (
    <div className="code-editor-grid">
      <fieldset>
        <legend>Общие параметры</legend>
        <div className="three-col">
          <label>
            Ожидаемое / известное d_min
            <input
              type="number"
              value={code.expected_min_distance ?? ""}
              onChange={event => onChange({
                expected_min_distance: optionalNumber(event.target.value),
              })}
              placeholder="не задано"
            />
          </label>
          <label>
            Syndrome t для этого кода
            <input
              type="number"
              min={0}
              value={code.syndrome_max_error_weight ?? ""}
              onChange={event => onChange({
                syndrome_max_error_weight: optionalNumber(event.target.value),
              })}
              placeholder="глобальное"
            />
          </label>
          <label>
            Chase inner t для этого кода
            <input
              type="number"
              min={0}
              value={code.chase_inner_decoder_max_error_weight ?? ""}
              onChange={event => onChange({
                chase_inner_decoder_max_error_weight: optionalNumber(event.target.value),
              })}
              placeholder="глобальное"
            />
          </label>
          <label>
            Chase p для этого кода
            <input
              type="number"
              min={1}
              value={code.chase_unreliable_positions_count ?? ""}
              onChange={event => onChange({
                chase_unreliable_positions_count: optionalNumber(event.target.value),
              })}
              placeholder="глобальное"
            />
          </label>
        </div>
      </fieldset>

      {code.family === "wavelet" && (
        <fieldset>
          <legend>Wavelet</legend>
          <label>
            h
            <textarea
              value={hText}
              onChange={event => {
                const parsed = parseBinaryVector(event.target.value);
                if (parsed !== null || event.target.value.trim() === "") {
                  onChange({ h: parsed });
                }
              }}
              placeholder="1, 0, 0, 1, ..."
            />
            <span className="field-hint">
              длина: {code.h?.length ?? 0}, вес: {code.h?.reduce((sum, value) => sum + value, 0) ?? 0}
            </span>
          </label>
          <label>
            g
            <textarea
              value={gText}
              onChange={event => {
                const parsed = parseBinaryVector(event.target.value);
                if (parsed !== null || event.target.value.trim() === "") {
                  onChange({ g: parsed });
                }
              }}
              placeholder="пусто = вычисляется/не используется согласно текущей реализации"
            />
            <span className="field-hint">
              длина: {code.g?.length ?? 0}, вес: {code.g?.reduce((sum, value) => sum + value, 0) ?? 0}
            </span>
          </label>
          <div className="three-col">
            <label>
              a
              <input type="number" value={code.a ?? 1} onChange={event => onChange({ a: Number(event.target.value) })} />
            </label>
            <label>
              b
              <input type="number" value={code.b ?? 1} onChange={event => onChange({ b: Number(event.target.value) })} />
            </label>
            <label>
              shift
              <input type="number" value={code.shift ?? 1} onChange={event => onChange({ shift: Number(event.target.value) })} />
            </label>
          </div>
        </fieldset>
      )}

      {(code.family === "bch" || code.family === "bch_derived") && (
        <fieldset>
          <legend>BCH</legend>
          <div className="three-col">
            <label>
              m
              <input
                type="number"
                min={1}
                value={code.bch_m ?? ""}
                onChange={event => onChange({ bch_m: optionalNumber(event.target.value) })}
              />
            </label>
            <label>
              Designed distance
              <input
                type="number"
                min={2}
                value={code.bch_designed_distance ?? ""}
                onChange={event => onChange({
                  bch_designed_distance: optionalNumber(event.target.value),
                })}
              />
            </label>
            <label>
              First root
              <input
                type="number"
                value={code.bch_first_root ?? 1}
                onChange={event => onChange({ bch_first_root: Number(event.target.value) })}
              />
            </label>
            <label>
              Primitive polynomial (integer)
              <input
                type="number"
                value={code.bch_primitive_polynomial ?? ""}
                onChange={event => onChange({
                  bch_primitive_polynomial: optionalNumber(event.target.value),
                })}
                placeholder="встроенный по m"
              />
            </label>
          </div>
        </fieldset>
      )}

      {code.family === "bch_derived" && (
        <fieldset>
          <legend>BCH-derived</legend>
          <div className="two-col">
            <label>
              Shortening count
              <input
                type="number"
                min={0}
                value={code.bch_shortening_count ?? ""}
                onChange={event => onChange({
                  bch_shortening_count: optionalNumber(event.target.value),
                })}
              />
            </label>
            <label>
              Puncture count
              <input
                type="number"
                min={0}
                value={code.bch_puncture_count ?? ""}
                onChange={event => onChange({
                  bch_puncture_count: optionalNumber(event.target.value),
                })}
              />
            </label>
          </div>
        </fieldset>
      )}

      {code.family === "goppa_derived" && (
        <fieldset>
          <legend>Goppa-derived</legend>
          <div className="three-col">
            <label>
              m
              <input
                type="number"
                min={1}
                value={code.goppa_m ?? ""}
                onChange={event => onChange({ goppa_m: optionalNumber(event.target.value) })}
              />
            </label>
            <label>
              Degree
              <input
                type="number"
                min={1}
                value={code.goppa_degree ?? ""}
                onChange={event => onChange({ goppa_degree: optionalNumber(event.target.value) })}
              />
            </label>
            <label>
              Support size
              <input
                type="number"
                min={1}
                value={code.goppa_support_size ?? ""}
                onChange={event => onChange({ goppa_support_size: optionalNumber(event.target.value) })}
              />
            </label>
            <label>
              Seed
              <input
                type="number"
                value={code.goppa_seed ?? 42}
                onChange={event => onChange({ goppa_seed: Number(event.target.value) })}
              />
            </label>
            <label>
              Primitive polynomial (integer)
              <input
                type="number"
                value={code.goppa_primitive_polynomial ?? ""}
                onChange={event => onChange({
                  goppa_primitive_polynomial: optionalNumber(event.target.value),
                })}
                placeholder="встроенный по m"
              />
            </label>
          </div>
        </fieldset>
      )}

      {code.family === "reed_solomon_binary" && (
        <fieldset>
          <legend>Generalized Reed–Solomon (binary)</legend>
          <div className="three-col">
            <label>Field degree m<input type="number" min={1} value={code.reed_solomon_m ?? ""} onChange={event => onChange({ reed_solomon_m: optionalNumber(event.target.value) })} /></label>
            <label>Symbol N<input type="number" min={1} value={code.reed_solomon_symbol_n ?? ""} onChange={event => onChange({ reed_solomon_symbol_n: optionalNumber(event.target.value) })} /></label>
            <label>Symbol K<input type="number" min={1} value={code.reed_solomon_symbol_k ?? ""} onChange={event => onChange({ reed_solomon_symbol_k: optionalNumber(event.target.value) })} /></label>
            <label>Primitive polynomial<input type="number" min={1} value={code.reed_solomon_primitive_polynomial ?? ""} onChange={event => onChange({ reed_solomon_primitive_polynomial: optionalNumber(event.target.value) })} placeholder="19 (0b10011)" /></label>
            <label>Evaluation points<input value={integerVectorToText(code.reed_solomon_evaluation_points)} onChange={event => onChange({ reed_solomon_evaluation_points: parseIntegerVector(event.target.value) })} placeholder="0, 1, 2, 3" /></label>
            <label>Column multipliers<input value={integerVectorToText(code.reed_solomon_column_multipliers)} onChange={event => onChange({ reed_solomon_column_multipliers: parseIntegerVector(event.target.value) })} placeholder="1, 3, 1, 3" /></label>
          </div>
          <p className="field-hint">Binary preview: n = {(code.reed_solomon_m ?? 0) * (code.reed_solomon_symbol_n ?? 0)}, k = {(code.reed_solomon_m ?? 0) * (code.reed_solomon_symbol_k ?? 0)}, R = {code.n > 0 ? (code.k / code.n).toFixed(3) : "—"}. {grsTargetHint}</p>
        </fieldset>
      )}
    </div>
  );
}
