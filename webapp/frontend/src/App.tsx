import { NavLink, Route, Routes } from "react-router-dom";
import { ExperimentPage } from "./pages/ExperimentPage";
import { ExperimentsPage } from "./pages/ExperimentsPage";
import { ImportExperimentPage } from "./pages/ImportExperimentPage";
import { NewExperimentPage } from "./pages/NewExperimentPage";

export default function App() {
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><strong>W/BCH</strong><span>research console</span></div>
      <nav>
        <NavLink to="/">Эксперименты</NavLink>
        <NavLink to="/new">Новый эксперимент</NavLink>
        <NavLink to="/import">Импорт эксперимента</NavLink>
      </nav>
      <div className="sidebar-note">Локальная лаборатория кодов и декодеров</div>
    </aside>
    <main className="content">
      <Routes>
        <Route path="/" element={<ExperimentsPage />} />
        <Route path="/new" element={<NewExperimentPage />} />
        <Route path="/import" element={<ImportExperimentPage />} />
        <Route path="/experiments/:id" element={<ExperimentPage />} />
      </Routes>
    </main>
  </div>;
}
