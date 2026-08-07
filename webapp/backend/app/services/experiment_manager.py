"""Управление локальной очередью экспериментов."""

import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.config import PROJECT_ROOT
from app.core.security import make_results_dir, resolve_results_dir
from app.db.database import SessionLocal
from app.models.experiment import Experiment, ExperimentStatus
from app.services.config_adapter import schema_to_research, validate_schema
from app.services.results_reader import read_summary
from research.config import ResearchConfig


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExperimentManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._run_slot = threading.Semaphore(1)
        self._processes: dict[str, subprocess.Popen[str]] = {}
        self._threads: dict[str, threading.Thread] = {}
        self.recover_interrupted()

    def recover_interrupted(self) -> None:
        with SessionLocal() as session:
            active = session.scalars(
                select(Experiment).where(
                    Experiment.status.in_(
                        [
                            ExperimentStatus.queued,
                            ExperimentStatus.validating,
                            ExperimentStatus.running,
                            ExperimentStatus.cancelling,
                        ]
                    )
                )
            ).all()
            for experiment in active:
                experiment.status = ExperimentStatus.interrupted
                experiment.finished_at = _utcnow()
                experiment.error_message = "Backend был перезапущен во время выполнения"
            session.commit()

    def create(self, name: str, description: str, schema: Any) -> Experiment:
        validation = validate_schema(schema)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        experiment_id = uuid.uuid4()
        results_dir = make_results_dir(experiment_id, name)
        config = schema_to_research(schema, results_dir=results_dir)
        config_json = json.dumps(config.to_json_dict(), ensure_ascii=False)
        log_path = str(Path(results_dir) / "experiment.log")

        Path(results_dir).mkdir(parents=True, exist_ok=True)
        Path(log_path).write_text("", encoding="utf-8")

        experiment = Experiment(
            id=str(experiment_id),
            name=name,
            description=description,
            status=ExperimentStatus.queued,
            config_json=config_json,
            results_dir=results_dir,
            log_path=log_path,
            progress_total=config.estimate_workload()["total_series"],
        )
        with SessionLocal() as session:
            session.add(experiment)
            session.commit()
            session.refresh(experiment)

        self.start(experiment.id)
        return experiment

    def start(self, experiment_id: str) -> None:
        with self._lock:
            if experiment_id in self._processes:
                return
            thread = threading.Thread(
                target=self._queued_run,
                args=(experiment_id,),
                daemon=True,
                name=f"experiment-{experiment_id[:8]}",
            )
            self._threads[experiment_id] = thread
            thread.start()

    def _queued_run(self, experiment_id: str) -> None:
        """Ожидает единственный доступный слот запуска."""
        with self._run_slot:
            with SessionLocal() as session:
                experiment = session.get(Experiment, experiment_id)
                if experiment is None or experiment.status == ExperimentStatus.cancelled:
                    with self._lock:
                        self._threads.pop(experiment_id, None)
                    return
            self._run(experiment_id)

    def _run(self, experiment_id: str) -> None:
        with SessionLocal() as session:
            experiment = session.get(Experiment, experiment_id)
            if experiment is None:
                return
            config_path = Path(experiment.results_dir) / "runtime_config.json"
            config_path.write_text(experiment.config_json, encoding="utf-8")
            log_path = Path(experiment.log_path)
            experiment.status = ExperimentStatus.validating
            experiment.started_at = _utcnow()
            session.commit()

        command = [sys.executable, "-m", "research.run_from_json", str(config_path)]
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            process = subprocess.Popen(
                command,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
                shell=False,
            )
            with self._lock:
                self._processes[experiment_id] = process

            with log_path.open("a", encoding="utf-8") as log:
                assert process.stdout is not None
                for line in process.stdout:
                    log.write(line)
                    log.flush()
                    self._consume_line(experiment_id, line)
                exit_code = process.wait()

            with SessionLocal() as session:
                experiment = session.get(Experiment, experiment_id)
                if experiment is not None:
                    experiment.exit_code = exit_code
                    experiment.finished_at = _utcnow()
                    if experiment.status == ExperimentStatus.cancelling:
                        experiment.status = ExperimentStatus.cancelled
                    elif exit_code == 0:
                        experiment.status = ExperimentStatus.completed
                    else:
                        experiment.status = ExperimentStatus.failed
                        if not experiment.error_message:
                            experiment.error_message = f"Процесс завершился с кодом {exit_code}"
                    session.commit()
        except Exception as exc:  # noqa: BLE001
            with SessionLocal() as session:
                experiment = session.get(Experiment, experiment_id)
                if experiment is not None:
                    experiment.status = ExperimentStatus.failed
                    experiment.finished_at = _utcnow()
                    experiment.error_message = str(exc)
                    session.commit()
        finally:
            with self._lock:
                self._processes.pop(experiment_id, None)
                self._threads.pop(experiment_id, None)

    def _consume_line(self, experiment_id: str, line: str) -> None:
        if not line.startswith("PROGRESS "):
            return
        try:
            payload = json.loads(line.removeprefix("PROGRESS "))
        except json.JSONDecodeError:
            return
        with SessionLocal() as session:
            experiment = session.get(Experiment, experiment_id)
            if experiment is None:
                return
            experiment.progress_payload = json.dumps(payload, ensure_ascii=False)
            if "completed" in payload:
                experiment.progress_completed = int(payload["completed"])
            if "total" in payload:
                experiment.progress_total = int(payload["total"])
            if payload.get("stage") == "running":
                experiment.status = ExperimentStatus.running
            if payload.get("stage") == "failed":
                experiment.error_message = str(payload.get("error", "Ошибка запуска"))
            session.commit()

    def cancel(self, experiment_id: str) -> bool:
        with self._lock:
            process = self._processes.get(experiment_id)
            thread = self._threads.get(experiment_id)
        if process is None:
            if thread is None:
                return False
            with SessionLocal() as session:
                experiment = session.get(Experiment, experiment_id)
                if experiment is None or experiment.status != ExperimentStatus.queued:
                    return False
                experiment.status = ExperimentStatus.cancelled
                experiment.finished_at = _utcnow()
                session.commit()
            return True
        with SessionLocal() as session:
            experiment = session.get(Experiment, experiment_id)
            if experiment is not None:
                experiment.status = ExperimentStatus.cancelling
                session.commit()
        process.terminate()
        return True

    def get(self, experiment_id: str) -> Experiment | None:
        with SessionLocal() as session:
            return session.get(Experiment, experiment_id)

    def config(self, experiment: Experiment) -> dict[str, Any]:
        return json.loads(experiment.config_json)

    def log(self, experiment: Experiment, tail: int = 500) -> list[str]:
        try:
            path = resolve_results_dir(experiment.results_dir) / "experiment.log"
        except ValueError:
            return []
        if not path.is_file():
            return []
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-tail:]

    def has_results(self, experiment: Experiment) -> bool:
        try:
            read_summary(experiment.results_dir)
            return True
        except (FileNotFoundError, ValueError):
            return False


manager = ExperimentManager()
