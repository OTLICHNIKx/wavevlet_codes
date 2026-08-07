import { Component, type ErrorInfo, type ReactNode } from "react";


export class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("UI error", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <main className="fatal-error">
          <div className="eyebrow">INTERFACE ERROR</div>
          <h1>Интерфейс не смог отобразить страницу</h1>
          <p>{this.state.error.message}</p>
          <button className="button primary" onClick={() => window.location.reload()}>
            Перезагрузить страницу
          </button>
        </main>
      );
    }
    return this.props.children;
  }
}
