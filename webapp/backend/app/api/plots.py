from collections import defaultdict
import csv
import io
import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.models.api import PlotExportRequest, PlotPreviewRequest
from app.services.experiment_manager import manager
from app.services.results_reader import read_summary, zero_adjusted_value


router = APIRouter(prefix="/api/plots", tags=["plots"])


@router.post("/preview")
def preview(request: PlotPreviewRequest) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)

    for experiment_id in request.experiment_ids:
        experiment = manager.get(experiment_id)
        if experiment is None:
            raise HTTPException(status_code=404, detail=f"Эксперимент {experiment_id} не найден")
        try:
            _, rows = read_summary(experiment.results_dir)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        for row in rows:
            if request.codes and row.get("code_name") not in request.codes:
                continue
            if request.decoders and row.get("decoder") not in request.decoders:
                continue
            ebn0 = row.get("ebn0_db")
            if not isinstance(ebn0, (int, float)):
                continue
            if request.ebn0_min is not None and ebn0 < request.ebn0_min:
                continue
            if request.ebn0_max is not None and ebn0 > request.ebn0_max:
                continue
            for metric in request.metrics:
                value = zero_adjusted_value(row, metric, request.zero_mode, request.epsilon)
                if value is None:
                    continue
                key = (experiment.name, str(row["code_name"]), str(row["decoder"]), metric)
                grouped[key].append({"x": float(ebn0), "y": value})

    series = []
    for (experiment_name, code, decoder, metric), points in sorted(grouped.items()):
        points.sort(key=lambda item: item["x"])
        series.append(
            {
                "name": f"{experiment_name} / {code} / {decoder} / {metric}",
                "experiment_name": experiment_name,
                "code": code,
                "decoder": decoder,
                "metric": metric,
                "x": [point["x"] for point in points],
                "y": [point["y"] for point in points],
            }
        )
    return {"series": series, "zero_mode": request.zero_mode}


@router.post("/export")
def export(request: PlotExportRequest) -> Response:
    dataset = preview(PlotPreviewRequest.model_validate(request.model_dump()))
    if request.format == "json":
        return Response(
            content=json.dumps(dataset, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=plot_dataset.json"},
        )
    if request.format != "csv":
        raise HTTPException(
            status_code=422,
            detail=(
                "Backend экспортирует csv/json; PNG, SVG и HTML "
                "экспортируются Plotly в браузере"
            ),
        )
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "series",
            "experiment_name",
            "code",
            "decoder",
            "metric",
            "ebn0_db",
            "value",
        ],
    )
    writer.writeheader()
    for series in dataset["series"]:
        for x, y in zip(series["x"], series["y"]):
            writer.writerow(
                {
                    "series": series["name"],
                    "experiment_name": series["experiment_name"],
                    "code": series["code"],
                    "decoder": series["decoder"],
                    "metric": series["metric"],
                    "ebn0_db": x,
                    "value": y,
                }
            )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=plot_dataset.csv"},
    )
