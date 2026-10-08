from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os

from . import models, schemas, database, certificate

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Bulk Certificate Generator API")

def process_job_background(job_id: int, event_name: str, date: str):
    db = database.SessionLocal()
    try:
        job = db.query(models.GenerationJob).filter(models.GenerationJob.id == job_id).first()
        if not job:
            return
        
        job.status = models.JobStatus.PROCESSING
        db.commit()
        
        certificates = db.query(models.Certificate).filter(models.Certificate.job_id == job_id).all()
        
        successful = 0
        failed = 0
        
        for cert in certificates:
            try:
                file_path = certificate.generate_certificate_pdf(
                    recipient_name=cert.recipient_name,
                    event_name=event_name,
                    date=date,
                    certificate_id=cert.id
                )
                cert.status = models.CertificateStatus.SUCCESS
                cert.file_path = file_path
                successful += 1
            except Exception as e:
                cert.status = models.CertificateStatus.FAILED
                cert.error_message = str(e)
                failed += 1
            
            db.commit()
        
        job.successful_generations = successful
        job.failed_generations = failed
        
        if failed == 0:
            job.status = models.JobStatus.COMPLETED
        elif successful == 0:
            job.status = models.JobStatus.FAILED
        else:
            job.status = models.JobStatus.COMPLETED_WITH_ERRORS
            
        db.commit()
    finally:
        db.close()


@app.post("/jobs", response_model=schemas.JobResponse, status_code=201)
def create_job(request: schemas.JobCreateRequest, background_tasks: BackgroundTasks, db: Session = Depends(database.get_db)):
    job = models.GenerationJob(
        total_recipients=len(request.recipients)
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    for recipient in request.recipients:
        cert = models.Certificate(
            job_id=job.id,
            recipient_name=recipient.name,
            recipient_email=recipient.email,
        )
        db.add(cert)
    
    db.commit()
    
    background_tasks.add_task(process_job_background, job.id, request.event_name, request.date)
    
    return job

@app.get("/jobs/{job_id}", response_model=schemas.JobResponse)
def get_job(job_id: int, db: Session = Depends(database.get_db)):
    job = db.query(models.GenerationJob).filter(models.GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/jobs/{job_id}/certificates", response_model=List[schemas.CertificateResponse])
def get_job_certificates(job_id: int, db: Session = Depends(database.get_db)):
    job = db.query(models.GenerationJob).filter(models.GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job.certificates

@app.get("/certificates/{certificate_id}")
def get_certificate_file(certificate_id: int, db: Session = Depends(database.get_db)):
    cert = db.query(models.Certificate).filter(models.Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    if cert.status != models.CertificateStatus.SUCCESS or not cert.file_path:
        raise HTTPException(status_code=400, detail="Certificate has not been generated successfully")
        
    if not os.path.exists(cert.file_path):
        raise HTTPException(status_code=404, detail="Certificate file not found on server")
        
    return FileResponse(
        path=cert.file_path,
        media_type="application/pdf",
        filename=os.path.basename(cert.file_path)
    )
