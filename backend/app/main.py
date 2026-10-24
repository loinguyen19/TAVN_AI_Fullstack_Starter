from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .parser import parse_torque_xml
from .validators.base import ValidationResult
from .validators.registry import run_all_validators

app = FastAPI(title="Torque Spec Validator")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/api/upload")
async def upload_file(file: UploadFile):
    if not file.filename or not file.filename.endswith(".xml"):
        raise HTTPException(400, "Only XML files are accepted")

    content = await file.read()
    try:
        document = parse_torque_xml(content, file.filename)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse XML: {e}")

    validations = run_all_validators(document)

    return {
        "filename": file.filename,
        "document_date": document.document_date,
        "notes": document.notes,
        "addresses": [
            {
                "code": a.code,
                "torque": a.torque,
                "notes": a.notes,
                "start_date": a.start_date,
                "end_date": a.end_date,
            }
            for a in document.addresses
        ],
        "validations": [v.model_dump() for v in validations],
    }
