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

from app.core.config import IMPORTED_RESULTS_SUBDIR, PROJECT_ROOT
from app.core.security import make_results_dir, resolve_results_dir
from app.db.database import SessionLocal
from app.models.experiment import Experiment, ExperimentSource, ExperimentStatus
from app.services.code_metadata import build_code_metadata_list
from app.services.config_adapter import schema_to_research, validate_schema
from app.services.csv_import import build_synthetic_config, parse_and_validate_csv
from app.services.package_io import (
    ParsedPackage,
    build_manifest,
    build_zip,
    parse_and_validate_package,
)
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

    def import_csv(
        self,
        name: str,
        description: str,
        filename: str,
        raw_bytes: bytes,
    ) -> Experiment:
        """
        Валидирует загруженный summary.csv и создаёт Imported Experiment.

        Никаких Monte-Carlo вычислений не запускается: файл копируется
        как есть, а конфигурация для отображения в UI строится только
        из данных, уже присутствующих в CSV.
        """
        result = parse_and_validate_csv(raw_bytes)

        experiment_id = uuid.uuid4()
        results_dir = make_results_dir(
            experiment_id, name, subdir=IMPORTED_RESULTS_SUBDIR
        )
        Path(results_dir).mkdir(parents=True, exist_ok=True)
        (Path(results_dir) / "summary.csv").write_bytes(raw_bytes)

        config_json = json.dumps(
            build_synthetic_config(result.rows, results_dir),
            ensure_ascii=False,
        )

        now = _utcnow()
        experiment = Experiment(
            id=str(experiment_id),
            name=name,
            description=description,
            status=ExperimentStatus.completed,
            source=ExperimentSource.imported_csv,
            original_filename=filename,
            created_at=now,
            started_at=now,
            finished_at=now,
            config_json=config_json,
            results_dir=results_dir,
            log_path="",
            exit_code=0,
            progress_completed=len(result.rows),
            progress_total=len(result.rows),
        )
        with SessionLocal() as session:
            session.add(experiment)
            session.commit()
            session.refresh(experiment)

        return experiment

    def has_runtime_config(self, experiment: Experiment) -> bool:
        try:
            path = resolve_results_dir(experiment.results_dir) / "runtime_config.json"
        except ValueError:
            return False
        return path.is_file()

    def has_experiment_log(self, experiment: Experiment) -> bool:
        if not experiment.log_path:
            return False
        try:
            results_path = resolve_results_dir(experiment.results_dir)
            log_path = Path(experiment.log_path).resolve()
        except ValueError:
            return False
        return log_path.is_relative_to(results_path) and log_path.is_file()

    def export_package(self, experiment: Experiment) -> bytes:
        if experiment.status != ExperimentStatus.completed:
            raise ValueError("Экспорт доступен только для завершённых экспериментов")

        results_path = resolve_results_dir(experiment.results_dir)
        summary_path = results_path / "summary.csv"
        if not summary_path.is_file():
            raise FileNotFoundError("summary.csv не найден")
        summary_bytes = summary_path.read_bytes()

        runtime_config_path = results_path / "runtime_config.json"
        runtime_config_bytes = (
            runtime_config_path.read_bytes()
            if runtime_config_path.is_file()
            else None
        )

        code_metadata_path = results_path / "code_metadata.json"
        if code_metadata_path.is_file():
            code_metadata_bytes = code_metadata_path.read_bytes()
        else:
            codes = json.loads(experiment.config_json).get("codes", [])
            code_metadata_bytes = json.dumps(
                build_code_metadata_list(codes), ensure_ascii=False, indent=2
            ).encode("utf-8")

        log_path = results_path / "experiment.log"
        experiment_log_bytes = (
            log_path.read_bytes()
            if log_path.is_file() and log_path.stat().st_size > 0
            else None
        )

        manifest = build_manifest(
            name=experiment.name,
            created_at=experiment.created_at.isoformat(),
            status=experiment.status.value,
            experiment_id=experiment.id,
        )

        return build_zip(
            manifest=manifest,
            summary_csv_bytes=summary_bytes,
            runtime_config_bytes=runtime_config_bytes,
            code_metadata_bytes=code_metadata_bytes,
            experiment_log_bytes=experiment_log_bytes,
        )

    def import_package(
        self,
        name: str,
        description: str,
        filename: str,
        raw_bytes: bytes,
    ) -> Experiment:
        """
        Валидирует experiment package и создаёт Imported Experiment.

        Никаких Monte-Carlo вычислений не запускается. Файлы пакета
        копируются как есть в собственное хранилище приложения.
        """
        parsed: ParsedPackage = parse_and_validate_package(raw_bytes)

        experiment_id = uuid.uuid4()
        display_name = name.strip() or str(
            parsed.manifest.get("name") or "imported experiment"
        )
        results_dir = make_results_dir(
            experiment_id, display_name, subdir=IMPORTED_RESULTS_SUBDIR
        )
        results_path = Path(results_dir)
        results_path.mkdir(parents=True, exist_ok=True)

        (results_path / "summary.csv").write_bytes(parsed.summary_csv_bytes)

        if parsed.runtime_config is not None:
            (results_path / "runtime_config.json").write_text(
                json.dumps(parsed.runtime_config, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            config_for_db = parsed.runtime_config
        else:
            config_for_db = build_synthetic_config(parsed.summary_rows, results_dir)

        if parsed.code_metadata is not None:
            (results_path / "code_metadata.json").write_text(
                json.dumps(parsed.code_metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        log_path_value = ""
        if parsed.experiment_log is not None:
            log_file = results_path / "experiment.log"
            log_file.write_text(parsed.experiment_log, encoding="utf-8")
            log_path_value = str(log_file)

        config_json = json.dumps(config_for_db, ensure_ascii=False)

        now = _utcnow()
        experiment = Experiment(
            id=str(experiment_id),
            name=display_name,
            description=description,
            status=ExperimentStatus.completed,
            source=ExperimentSource.imported_package,
            original_filename=filename,
            created_at=now,
            started_at=now,
            finished_at=now,
            config_json=config_json,
            results_dir=results_dir,
            log_path=log_path_value,
            exit_code=0,
            progress_completed=len(parsed.summary_rows),
            progress_total=len(parsed.summary_rows),
        )
        with SessionLocal() as session:
            session.add(experiment)
            session.commit()
            session.refresh(experiment)

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
