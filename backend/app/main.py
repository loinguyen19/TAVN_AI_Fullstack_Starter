"""HTTP layer.

Routing, status codes and response shaping only. All orchestration lives in
`services.ReportService`; all persistence lives behind `repository`. The router
never touches the database directly.
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .dependencies import get_report_service, get_repository
from .services import (
    DocumentParseError,
    ReportNotFound,
    ReportService,
    UnsupportedFileType,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_repository().initialise()
    yield


app = FastAPI(title="Torque Spec Validator", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.post("/api/reports", status_code=201)
async def create_report(
    file: UploadFile,
    service: ReportService = Depends(get_report_service),
):
    """Validate an uploaded XML document and store the resulting report."""
    content = await file.read()
    try:
        return service.create_from_file(content, file.filename)
    except UnsupportedFileType as exc:
        raise HTTPException(400, str(exc)) from exc
    except DocumentParseError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/reports")
def list_reports(
    limit: int = 50,
    service: ReportService = Depends(get_report_service),
):
    """Past reports, newest first."""
    return service.list_reports(limit=limit)


@app.get("/api/reports/{report_id}")
def read_report(
    report_id: int,
    service: ReportService = Depends(get_report_service),
):
    """A single stored report, in the same shape as the creation response."""
    try:
        return service.get_report(report_id)
    except ReportNotFound as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/reports/{report_id}/export.csv")
def export_report_csv(
    report_id: int,
    service: ReportService = Depends(get_report_service),
):
    """Findings for one report as CSV."""
    try:
        content, filename = service.export_report_csv(report_id)
    except ReportNotFound as exc:
        raise HTTPException(404, str(exc)) from exc

    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/validators")
def list_validators(service: ReportService = Depends(get_report_service)):
    """Registered validators and the rationale for each."""
    return service.available_validators()
