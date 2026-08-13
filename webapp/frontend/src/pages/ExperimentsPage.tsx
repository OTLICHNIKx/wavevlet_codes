import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Experiment } from "../types";

const SOURCE_LABELS: Record<string, string> = {
  local: "Локальный расчёт",
  imported_csv: "Импортирован (CSV)",
  imported_package: "Импортирован (package)",
};

export function ExperimentsPage() {
  const [items, setItems] = useState<Experiment[]>([]);
  const [error, setError] = useState("");
  const refresh = () => api.experiments().then(setItems).catch((e: Error) => setError(e.message));
  useEffect(() => { refresh(); }, []);
  return <section>
    <header className="page-header"><div><div className="eyebrow">LAB / RUNS</div><h1>Эксперименты</h1><p>Запуски, статусы и результаты моделирования каналов.</p></div><div style={{ display: "flex", gap: 8 }}><Link className="button" to="/import">⬇ Импорт</Link><Link className="button primary" to="/new">+ Новый запуск</Link></div></header>
    {error && <div className="alert error">{error}</div>}
    <div className="toolbar"><span className="muted">{items.length} запусков</span><button className="button" onClick={refresh}>Обновить</button></div>
    <div className="table-wrap"><table><thead><tr><th>Название</th><th>Статус</th><th>Источник</th><th>Создан</th><th>Коды</th><th>Сообщения</th><th>Eb/N0</th></tr></thead><tbody>
      {items.map(item => <tr key={item.id}><td><Link to={`/experiments/${item.id}`} className="table-link">{item.name}</Link></td><td><span className={`status ${item.status}`}>{item.status}</span></td><td>{item.source !== "local" && <span className="badge">{SOURCE_LABELS[item.source] || item.source}</span>}</td><td>{new Date(item.created_at).toLocaleString()}</td><td>{item.config.codes.map(c => c.name).join(", ")}</td><td>{item.config.message_count}</td><td>{item.config.ebn0_db_values[0]} ... {item.config.ebn0_db_values.at(-1)}</td></tr>)}
    </tbody></table>{items.length === 0 && <div className="empty">Запусков пока нет. Создайте первый эксперимент.</div>}</div>
  </section>;
}
