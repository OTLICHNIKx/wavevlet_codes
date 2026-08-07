import { useEffect, useRef } from "react";
import type { Config, Data, Layout } from "plotly.js";


type PlotlyApi = typeof import("plotly.js");


export function normalizePlotly(module: unknown): PlotlyApi {
  const candidate = module as { default?: PlotlyApi };
  return candidate.default || module as PlotlyApi;
}


export function PlotlyChart(props: {
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
        props.data,
        props.layout,
        { responsive: true, displaylogo: false, ...props.config },
      ).then(() => {
        if (!disposed && container.current) props.onReady?.(container.current);
      });
    }).catch(error => {
      console.error("Plotly initialization failed", error);
    });

    return () => {
      disposed = true;
      if (!container.current) return;
      import("plotly.js-dist-min").then(module => {
        normalizePlotly(module).purge(container.current as HTMLElement);
      });
    };
  }, [props.data, props.layout, props.config, props.onReady]);

  return <div ref={container} className="plotly-host" />;
}
