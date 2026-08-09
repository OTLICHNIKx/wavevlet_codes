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


export function CodeConfigEditor({ code, onChange }: Props) {
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
    </div>
  );
}
