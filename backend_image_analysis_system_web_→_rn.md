# Backend — Image Analysis System (Web first, React Native later)

> Detailed markdown for the entire backend system powering image analysis: capture ingestion, preprocessing, model inference, metrics extraction, storage, retraining pipeline, security, deployment, and observability. Designed for a self-hosted architecture (no external API keys).

---

## Table of contents
1. Overview
2. System components
3. Data flow (detailed)
4. API specification (endpoints + schemas)
5. Processing pipeline & job orchestration
6. Model hosting & inference options
7. Storage, data retention & privacy
8. Database schemas
9. Training pipeline & data labeling
10. Security, access control & compliance
11. Observability, logging & metrics
12. CI/CD & deployment
13. Scalability & cost considerations
14. Testing & QA
15. Operational runbook
16. Roadmap & extension points
17. Appendix: sample payloads, env vars, Docker snippets

---

## 1. Overview
This backend is responsible for all server-side aspects of image analysis for the web-first capture app. The primary goals:

- Accept user-captured images (front, side, portrait) and optional reference card image.
- Validate, sanitize, and queue images for processing.
- Run configurable inference steps (card detection, pose/keypoints, skin segmentation, color calibration, circumference regressors) either in-browser (preferred) or server-side when opted-in.
- Store derived metrics and (with consent) anonymized capture artifacts for model improvement.
- Provide secure partner/tailor/export APIs and an admin portal for reviewing training data.
- Be fully self-hosted (no third-party API keys). Models and data live on your infrastructure.

Design principles:
- Privacy-first: default local processing; server used only for opt-in uploads.
- Modular: each processing step is a separate task to allow retries and scaling.
- Auditable: every image and derived metric is logged with provenance.
- Easily deployable using Docker / Kubernetes.

---

## 2. System components

### 2.1 Public Web API (FastAPI)
- Responsible for auth, receiving uploads, returning processed results, and user management.
- Exposes endpoints described in Section 4.

### 2.2 Inference/Worker Cluster
- A set of worker services (Docker containers) that perform CPU/GPU-bound tasks.
- Orchestrated via Celery + RabbitMQ/Redis (Celery for Python) or via a lightweight queue like RQ for simpler setups.

### 2.3 Model Host & Storage
- Models stored as static files on your server or served from MinIO (S3-compatible) on your infra.
- Model formats: ONNX (server), TF SavedModel/TF Lite (server & mobile), TF.js (web), TFLite (mobile).

### 2.4 Object Storage (MinIO)
- Stores raw images (opt-in), processed artifacts, model artifacts, and backups.

### 2.5 Database (Postgres)
- Stores user data, capture metadata, derived metrics, audit logs, processing statuses, partner data.

### 2.6 Admin Portal
- For dataset reviewers, QA, label correction, partner/tailor management.
- Allows export of CSV/PDF "tailor-ready" measurement sheets.

### 2.7 Monitoring & Logging Stack
- Prometheus + Grafana for metrics.
- ELK (Elasticsearch + Logstash + Kibana) or Loki + Grafana for logging.

### 2.8 Training / Experimentation Environment
- GPU-enabled host(s) for training. Use DVC for data versioning and MLFlow for experiment tracking.

### 2.9 CI/CD
- GitHub Actions (self-hosted runner optional) to build and deploy containers, push model versions to model host, and run tests.

---

## 3. Data flow (detailed)

1. **Client-side capture** (preferred): the React web app runs TF.js/MediaPipe locally to compute keypoints/segmentation and performs color calibration. The client may submit either:
   - only derived metrics (JSON) and a low-resolution anonymized image. or
   - raw full-resolution images (opt-in).

2. **Upload**: Client calls `POST /api/upload-capture` with the chosen payload. If raw images are included, they must be encrypted on transit via HTTPS.

3. **Ingest validation**: API server validates formats, checks consent flags, strips EXIF if needed, and places a job in the processing queue.

4. **Queue & Worker**: Worker picks up the job and executes the pipeline steps (card detection → color calibration → pose/keypoints refinement → segmentation → regressor inference → confidence scoring).

5. **Derived metrics**: Worker stores results in Postgres (capture table) and optionally stores any processed images/artifacts in MinIO.

6. **Notification**: API sends a webhook or updates job status; client polls `GET /api/capture/{id}/results` or receives push via websocket.

7. **Admin**: Admin portal can fetch images and results for manual verification and labeling. Approved datasets get exported to the training store.

8. **Retraining**: Labeled data exported to DVC for model retraining. New models are tested and promoted to the model host.

---

## 4. API specification (summary)
**Base URL**: `https://<your-server>/api/v1`

### Auth
- **POST /auth/register** - register user (email, password) — returns token.
- **POST /auth/login** - login — returns JWT.
- **GET /auth/me** - current user.

### Capture Upload & Results
- **POST /capture** — upload images / metrics
  - Body: `multipart/form-data` with `front.jpg`, `side.jpg`, `portrait.jpg`, `ref.jpg` (optional), or JSON `{metrics: {...}, capture_meta:{...}}` for derived-metrics-only flow.
  - Query flags: `store_images=true|false` (must match user's consent).
  - Response: `{ capture_id, status: 'queued' }`.

- **GET /capture/{id}/status** — returns status, queue position.

- **GET /capture/{id}/results** — returns final JSON with metrics (see schema below).

- **POST /capture/{id}/manual-adjust** — submit keypoint corrections.

### Admin & Dataset
- **GET /admin/captures** — list captures for review.
- **POST /admin/label/{capture_id}** — label ground-truth measurements (for training).

### Partner / Tailor APIs
- **POST /partner/upload-batch** — allow boutiques to upload customer measurements in bulk (CSV/JSON).
- **GET /partner/{id}/exports** — download tailor-ready PDFs.

### Webhook / Notification
- **POST /webhook/capture-complete** — optional webhook endpoint for partners to receive completed results.


### Result JSON Schema (example)

### Editable Measurements & User Overrides

Users must be able to review and edit any extracted body measurements and related metrics before those values are treated as "final". This section describes the expected API behaviour, UX hooks, and server-side handling for user edits.

**Principles**:
- Keep the original detected metrics immutable and store edits as a separate, auditable version. Never overwrite the original raw result without preserving history.
- Edits lower the automated confidence for that capture until a human or verification step approves them.
- Allow users to add a short note explaining the reason for the edit (fit preference, measurement correction, clothing style choice).
- Allow tailors/admins to review and approve edits; approved edits can be promoted to ground-truth for training after consent.

**New/edit endpoints**:
- **PATCH /capture/{id}/metrics** — user-submitted adjustments (auth required).
  - Body: `{ "adjusted_metrics": {"waist_cm": 76.0, ...}, "notes": "Measured with tape at home", "source": "user" }`
  - Server behaviour: validate schema, store in `user_adjustments` table (see DB schema), set `captures.status` to `edited`, update `capture_metrics` with a `latest_adjustment_id` pointer while keeping `metrics_json.original` intact, return the merged metrics and a lowered `overall_confidence` field.

- **POST /capture/{id}/adjustments/approve** — admin/tailor endpoint to approve an adjustment (role-based access).
  - Body: `{ "adjustment_id": "uuid", "approver_id": "uuid", "approve": true }`
  - Server behaviour: mark adjustment as approved, set `capture_metrics.metrics_json.current` to the adjusted values, mark `approved_by` and `approved_at`, and optionally enqueue the adjusted record into the training export queue (only with user's explicit consent).

- **GET /capture/{id}/metrics/history** — list original + all adjustments with metadata (who, when, notes, approved flag).

**UX hooks**:
- Show original metric with confidence and a quick-edit button beside each measurement (e.g., "Waist: 75 cm (±4 cm) [edit]").
- When the user edits a value, show an inline slider + numeric input, a required short note (optional to relax later), and a prominent reminder that edits will be saved as their preference and can be shared with tailors.
- After saving, update the result UI to show the adjusted value and an "edited by you" badge with a link to the history.

**Data handling & training**:
- Store adjustments separately and only mark as usable for model retraining if the user explicitly opts in to share their corrected data for training.
- Approved adjustments (by tailor/admin) may be turned into ground truth faster, but still require explicit user consent before being used in training datasets.


```json
{
  "capture_id": "uuid-v4",
  "user_id": "uuid-v4",
  "timestamp": "2025-12-10T12:33:45Z",
  "metrics": {
    "height_cm": 172.4,
    "shoulder_width_cm": 41.2,
    "chest_circumference_cm": 95.6,
    "waist_circumference_cm": 75.0,
    "hip_circumference_cm": 99.2,
    "inseam_cm": 78.3,
    "torso_length_cm": 52.1,
    "neck_circumference_cm": 36.5
  },
  "skin": {
    "ita": 18.3,
    "lab": {"L": 56.2, "a": 13.1, "b": 16.5},
    "monk_bucket": 6,
    "undertone": "warm",
    "palette": [{"hex":"#8B4B2F","reason":"high-contrast warm"}]
  },
  "shape": {"type":"hourglass","confidence":0.82},
  "quality": {"lighting_ok":true, "card_detected":true, "overall_confidence":0.78}
}
```

---

## 5. Processing pipeline & job orchestration
Each capture job runs as a pipeline of discrete tasks. These tasks are idempotent and resumable.

### Pipeline stages
1. **Pre-check**: validate files, consent, image integrity.
2. **Card detection + perspective correction**:
   - Detect ARTag/rectangle using OpenCV (Canny + contour detection) and compute homography.
   - If card found, compute pixel→cm scale and color calibration matrix.
3. **Color calibration**:
   - Apply Bradford transform or simple gray-world correction using the card's neutral patch.
4. **Pose & Keypoint refinement**:
   - Run pose detection model (MoveNet / BlazePose) and optionally refine using PnP or iterative optimization.
5. **Segmentation (skin regions)**:
   - Run segmentation model; extract patches (face, neck, inner arm).
6. **Skin metrics computation**:
   - Convert selected patch average color to CIELab → compute ITA → map to Monk bucket.
7. **Width & depth extraction**:
   - Compute pixel distances (shoulder, chest width, hip width), use homography-corrected coordinates.
8. **Circumference regression**:
   - Input scaled widths + depths + height to the regressor to predict circumferences.
9. **Post-processing & confidence scoring**:
   - Merge per-stage confidences; flag low-confidence measures and recommend manual review.
10. **Persistence**:
   - Store final metrics in Postgres, processed images/artifacts in MinIO.
11. **Notify & Export**:
   - Trigger webhook, update status, and generate downloadable PDF for user/tailor.

### Orchestration choices
- **Celery** with RabbitMQ / Redis: robust, supports retries and scheduling.
- **Kubernetes CronJobs** and **Work queues**: if running in K8s.
- **Lightweight alternative**: RQ (Redis Queue) with worker pool for simpler infra.

---

## 6. Model hosting & inference options

### Option A — Server-side inference
- Host heavy models (PyTorch/TorchServe or ONNX) behind an internal endpoint: `http://inference.svc/models/pose/predict`.
- Use gRPC or REST to send preprocessed images.
- Pros: can use GPU acceleration and larger models. Cons: requires GPU infra and increases privacy burden.

### Option B — Client-side inference (preferred)
- Distribute TF.js/TFLite models to the browser/mobile app; default processing happens client-side and only metrics are uploaded.
- Pros: privacy, lower infra cost, faster for user. Cons: browser performance limitations.

### Option C — Hybrid
- Lightweight preprocessing & pose on client, heavy regressors or validation on server when user opts in or if client reports low confidence.

### Model versioning
- Keep models in `models/<model-name>/vX.Y/` and store metadata (`models.json`) that admin can update. Workers and clients read model manifest.
- Use DVC or a simple tagging scheme to manage versions; upload artifacts to MinIO.

---

## 7. Storage, data retention & privacy

### Storage roles
- **MinIO buckets**:
  - `raw-captures`: opt-in raw images (encrypted at rest)
  - `processed-artifacts`: aligned/corrected images and masks
  - `models`: model artifacts
  - `exports`: generated PDF & CSV exports

### Retention policy
- Default: do not store raw images (or delete after 24 hours) unless user explicitly opts-in. Keep derived metrics indefinitely unless user requests deletion.
- For opt-in training datasets: store images for N days (e.g., 365) and allow deletion by request.

### Encryption & transmission
- TLS 1.3 for in-flight
- AES-256 for at-rest in MinIO.
- Use signed, expiring URLs for temporary access to image objects when generating exports.

### Data access
- Admin-only access to raw images requires elevated role and audit logs.
- Provide endpoints for user data export and deletion (`/me/export`, `/me/delete`).

---

## 8. Database schemas

### 8.1 `users` table
- `id` (uuid, pk), `email`, `password_hash`, `created_at`, `last_login`, `consent_flags` (json)

### 8.2 `captures` table
- `id` (uuid, pk), `user_id`, `status` (queued/processing/done/failed), `created_at`, `updated_at`, `store_images` (bool), `source` (web|mobile)

### 8.3 `capture_metrics` table
- `id` (uuid), `capture_id`, `metrics_json` (jsonb), `skin_json` (jsonb), `shape_json` (jsonb), `quality_json` (jsonb), `model_versions` (json)

### 8.4 `artifacts` table
- `id`, `capture_id`, `bucket_path`, `artifact_type` (aligned, mask, heatmap), `created_at`

### 8.5 `labels` table (admin-labeled GT)
- `id`, `capture_id`, `labeler_id`, `measurements_json`, `approved` (bool), `notes`

### 8.6 `audit_logs`
- `id`, `actor_id`, `action`, `resource_type`, `resource_id`, `metadata`, `timestamp`

### 8.7 `user_adjustments` table (new)
- `id` (uuid, pk)
- `capture_id` (fk)
- `user_id` (fk)
- `original_metrics_json` (jsonb) — snapshot of metrics before adjustment
- `adjusted_metrics_json` (jsonb) — user-supplied adjustments
- `notes` (text) — user's reason or context
- `source` (enum: 'user','tailor','admin')
- `approved` (bool) — default false
- `approver_id` (nullable uuid)
- `approved_at` (nullable timestamp)
- `created_at` (timestamp)

Notes:
- When a user submits adjustments via the API, the backend MUST create a `user_adjustments` row and link it from `capture_metrics` by setting `latest_adjustment_id`.
- The system preserves `metrics_json.original` inside `capture_metrics` and maintains `metrics_json.current` which reflects the latest active (approved or unapproved) measurement shown to the user.

---

## 9. Training pipeline & data labeling

### Data ingestion
- Admin portal or ingestion API allows dataset curators to mark captures for training and export batches.
- Use DVC to version datasets; store raw + processed in DVC remote (MinIO).

### Model training
- Use PyTorch or TF. Keep training scripts in `ml/train/` with reproducible configs (Hydra or simple YAML). Track runs in MLflow.
- Use Augmentation: lighting jitter, scale, small rotations, occlusion simulation.

### Evaluation
- Create evaluation splits by skin-tone bucket and body-shape clusters.
- Track MAE per bucket and unit tests that assert no single bucket has >X% worse performance vs baseline.

### Promotion
- After validating, export model to `models/<name>/vX.Y/` and update `models.json` manifest. CI deploys new model files to static host.

---

## 10. Security, access control & compliance

### Authentication
- JWT tokens (short TTL) with refresh tokens stored in DB. HTTPS mandatory.

### Roles
- `user`, `admin`, `labeler`, `partner` with role-based access control enforced at API layer.

### Secrets
- Store secrets in Vault or at minimum in environment variables on the host; avoid embedding in code.

### Audit & compliance
- Keep audit logs for all admin/download actions.
- Provide endpoints to support GDPR-like requests (export/delete) and retention policies.

---

## 11. Observability & logging

### Metrics
- Track: captures queued, processing time per stage, per-model latency, error rates, quality-fail rates, downloads.
- Use Prometheus exporters to collect metrics from API and worker containers.

### Logs
- Structured logs (JSON) with trace IDs. Send to Elasticsearch or Loki. Retain logs for 90 days by default.

### Tracing
- Use Jaeger/OpenTelemetry for tracing API → worker → model calls to debug slow paths.

---

## 12. CI/CD & deployment

*Deployment guide intentionally omitted for now; will be added later after testing and validation.*

## 13. Scalability & cost considerations
- CPU-bound tasks (OpenCV, TF CPU) scale horizontally; use small worker instances.
- GPU-bound tasks (large models) require GPU-equipped nodes; minimize server-side heavy inference by preferring client-side inference.
- Use autoscaling pools and spot/preemptible instances for non-critical batch training.

---

## 14. Testing & QA
- Unit tests for: color conversion utils, image metadata parsing, DB CRUD operations, auth flows.
- Integration tests: end-to-end upload → queue → worker → result with sample images.
- Bias tests: run a test battery across skin-tone buckets and assert per-bucket MAE thresholds.
- Load tests: simulate concurrent uploads and worker throughput.

---

## 15. Operational runbook
Include this in operations documentation (short version here):

- **Worker stuck**: check RabbitMQ/Redis queue length, inspect logs, restart worker pod.
- **Model regression**: compare logs & metrics for new model version; rollback by updating `models.json` and redeploy older model directory.
- **Data deletion request**: run `DELETE /user/{id}/data` flow, purge MinIO objects and DB rows, create audit entry.
- **Storage full**: rotate old artifacts, alert on disk usage, and expand MinIO volume.

---

## 16. Roadmap & extension points
- **Phase 1**: Web-first, client-side inference default; server-side optional.
- **Phase 2**: React Native with on-device TFLite models and local-only mode.
- **Phase 3**: Tailor partner portal with batch imports and invoicing.
- **Phase 4**: Advanced feature: brand-specific sizing recommendations and shopping integration.

---

## 17. Appendix

### 17.1 Sample env vars
```
DATABASE_URL=postgres://user:pass@db:5432/appdb
MINIO_ENDPOINT=minio.local
MINIO_ACCESS_KEY=youraccess
MINIO_SECRET_KEY=yoursecret
RABBITMQ_URL=amqp://rabbitmq:5672/
JWT_SECRET=supersecret
MODEL_MANIFEST_URL=https://yourdomain.com/models/models.json
```

### 17.2 Sample Docker Compose (minimal)
```yaml
version: '3.8'
services:
  db:
    image: postgres:15
    volumes: [ 'pgdata:/var/lib/postgresql/data' ]
  minio:
    image: minio/minio
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    command: server /data
    ports: [ '9000:9000' ]
  rabbitmq:
    image: rabbitmq:3-management
    ports: [ '5672:5672', '15672:15672' ]
  api:
    build: ./backend
    environment: [ DATABASE_URL, MINIO_*, RABBITMQ_URL, JWT_SECRET ]
    ports: [ '8000:8000' ]
  worker:
    build: ./worker
    environment: [ DATABASE_URL, MINIO_*, RABBITMQ_URL ]
volumes:
  pgdata: {}
```

### 17.3 Sample result JSON
(See Section 4 result schema.)

### 17.4 Useful commands
- **Run migrations**: `alembic upgrade head` (if using Alembic)
- **Start worker**: `celery -A worker.app worker --loglevel=info`
- **Rebuild models**: `scripts/train_and_export.sh --config=configs/regressor.yaml`

---

> End of document. This file is the canonical backend reference for the image analysis subsystem. Use it as the blueprint for implementation, onboarding, and ops.

