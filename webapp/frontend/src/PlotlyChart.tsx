import { useEffect, useRef } from "react";
import type { Config, Data, Layout } from "plotly.js";

type PlotlyApi = typeof import("plotly.js");

export function normalizePlotly(module: unknown): PlotlyApi {
  const candidate = module as { default?: PlotlyApi };
  return candidate.default || module as PlotlyApi;
}

export function PlotlyChart({
  data,
  layout,
  config,
  onReady,
}: {
  data: Data[];
  layout: Partial<Layout>;
  config?: Partial<Config>;
  onReady?: (element: HTMLElement) => void;
}) {
  const container = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let disposed = false;

    import("plotly.js-dist-min").then(module => {
      if (disposed || !container.current) return;
      const Plotly = normalizePlotly(module);
      return Plotly.react(
        container.current,
        data,
        layout,
        { responsive: true, displaylogo: false, ...config },
      ).then(() => {
        if (!disposed && container.current) onReady?.(container.current);
      });
    }).catch(error => {
      console.error("Plotly initialization failed", error);
    });

    // При обновлении данных и layout Plotly.react обновляет существующий DOM-узел.
    // Не очищаем его здесь: это уничтожило бы текущий пользовательский zoom.
    return () => {
      disposed = true;
    };
  }, [config, data, layout, onReady]);

  useEffect(() => () => {
    const element = container.current;
    if (!element) return;
    import("plotly.js-dist-min").then(module => {
      normalizePlotly(module).purge(element);
    });
  }, []);

  return <div ref={container} className="plotly-host" />;
}
