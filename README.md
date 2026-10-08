# Bulk Certificate Generator Backend

## Project Overview
This project is a backend service for bulk generation of certificates. It allows users to submit a list of recipients for an event, validates the data, generates a PDF certificate for each recipient using ReportLab, and tracks the job's progress in an SQLite database. It is designed to be simple, fast, and easy to maintain.

## Technologies Used
- **Python**: Primary programming language.
- **FastAPI**: Modern, fast web framework for building APIs.
- **SQLite & SQLAlchemy**: Database and ORM for storing generation jobs and certificates.
- **Pydantic**: Data validation and serialization.
- **ReportLab**: PDF generation library.
- **pytest**: Testing framework.

## Setup Instructions

### Prerequisites
- Python 3.9+ installed on your system.

### Installation Commands

1. Clone or download the repository.
2. Navigate to the project directory:
   ```bash
   cd bulk-certificate-generator
   ```
3. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
4. Activate the virtual environment:
   - On Windows:
     ```bash
     .\.venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source .venv/bin/activate
     ```
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### How to Run the Application
Start the FastAPI application using Uvicorn:
```bash
uvicorn app.main:app --reload
```
The server will start at `http://127.0.0.1:8000`. You can access the interactive Swagger API documentation at `http://127.0.0.1:8000/docs`.

### How to Run Tests
To run the automated tests with pytest, execute:
```bash
python -m pytest
```

## API Endpoints

### 1. Create a Generation Job
**POST** `/jobs`
Creates a certificate generation job and starts background processing.

**Example Request:**
```json
{
  "event_name": "Python Conference 2026",
  "date": "2026-10-08",
  "recipients": [
    {
      "name": "Alice Smith",
      "email": "alice@example.com"
    },
    {
      "name": "Bob Jones",
      "email": "bob@example.com"
    }
  ]
}
```

**Example Response:**
```json
{
  "id": 1,
  "status": "PENDING",
  "total_recipients": 2,
  "successful_generations": 0,
  "failed_generations": 0,
  "created_at": "2026-10-08T10:00:00Z"
}
```

### 2. Get Job Status
**GET** `/jobs/{job_id}`
Returns job status and progress.

**Example Response:**
```json
{
  "id": 1,
  "status": "COMPLETED",
  "total_recipients": 2,
  "successful_generations": 2,
  "failed_generations": 0,
  "created_at": "2026-10-08T10:00:00Z"
}
```

### 3. Get Job Certificates
**GET** `/jobs/{job_id}/certificates`
Returns the list of certificates associated with a job.

**Example Response:**
```json
[
  {
    "id": 1,
    "job_id": 1,
    "recipient_name": "Alice Smith",
    "recipient_email": "alice@example.com",
    "status": "SUCCESS",
    "file_path": "generated_certificates\\cert_1.pdf",
    "error_message": null
  }
]
```

### 4. Download a Certificate PDF
**GET** `/certificates/{certificate_id}`
Returns the actual generated PDF file as an attachment. If the certificate hasn't been generated yet or failed, an appropriate HTTP error is returned.

## Architecture & Important Design Decisions

- **Background Processing without Extra Infrastructure**: The requirements explicitly prohibited introducing extra tools like Celery or Redis for background processing to keep the project simple. FastAPI's built-in `BackgroundTasks` feature is used to achieve asynchronous background processing directly within the web worker process. This keeps the initial HTTP request fast while handling the bulk generation separately.
- **Resilience**: The background job loops through all recipients and isolates exceptions. If one PDF generation fails, the error is saved to the specific certificate record and the job continues to process the remaining recipients.
- **Database**: SQLite is chosen for minimal setup, working flawlessly out-of-the-box. SQLAlchemy serves as the ORM to easily map Python classes to database tables and relationship mappings (`GenerationJob` and `Certificate`).
- **Data Validation**: Pydantic models automatically validate input formats (e.g., minimum length strings, valid email formats). Invalid inputs are rejected immediately with descriptive HTTP 422 error responses.

## Certificate Generation Flow
1. **Request Validation**: The `/jobs` endpoint validates the input payload.
2. **Database Initialization**: A `GenerationJob` is created with a `PENDING` status. `Certificate` records for each recipient are also initialized as `PENDING`.
3. **Response**: The API immediately responds with the created job ID and status.
4. **Background Task**: FastAPI hands off execution to a background task which iterates through the certificates.
5. **PDF Generation**: `ReportLab` generates a customized PDF. It updates the DB with success or error statuses.
6. **Completion**: Once all are processed, the overall Job status is updated to `COMPLETED` (or `COMPLETED_WITH_ERRORS` / `FAILED`).

## Future Improvements
- **Storage**: Currently, certificates are saved directly to the local disk. In a production environment, an integration with a cloud storage provider like AWS S3 or Google Cloud Storage would be preferred.
- **Pagination**: The GET endpoints could support limit and offset pagination.
- **Templating**: A customizable templating engine could be built on top of ReportLab to allow users to specify arbitrary template variables.
