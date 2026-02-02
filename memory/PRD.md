# DQ Sentinel - Product Requirements Document

## Original Problem Statement
Build a full-stack web app called "DQ Sentinel" - a Data Quality monitoring tool with:
- CSV upload (drag & drop)
- 10 DQ rules (null rate, duplicates, unique key, numeric range, regex email/phone/zip, date validation, categorical values, row count anomaly, outlier detection)
- Run History page
- Reports with overall score + rule table
- Download JSON/HTML reports
- Demo button for e-commerce data with intentional issues

### User Choices
- Package manager: npm (with --legacy-peer-deps)
- UI theme: Light theme, clean professional dashboard
- Additional features: Core features only (no email, no scheduled runs)
- Demo data: E-commerce dataset (orders/customers/products)
- NO Emergent packages, NO GPU packages, NO visual-edits/babel-metadata plugins

## User Personas
1. **Data Engineer**: Monitors data pipeline quality, needs quick validation of CSV exports
2. **Data Analyst**: Validates data before analysis, needs clear PASS/FAIL indicators
3. **QA Engineer**: Tests data integrity, needs sample bad rows for debugging

## Core Requirements (Static)
1. CSV file upload with drag & drop
2. 10 comprehensive DQ rules
3. Run history tracking with timestamps
4. JSON and HTML report downloads
5. Demo mode with intentional data issues
6. MongoDB for data persistence
7. FastAPI backend with /api prefix
8. React + Tailwind + Shadcn UI frontend

## What's Been Implemented (Feb 2, 2026)

### Backend (server.py)
- [x] POST /api/upload - CSV upload returning dataset_id
- [x] POST /api/run - Run DQ checks on dataset
- [x] POST /api/demo - Generate e-commerce demo data with issues
- [x] GET /api/runs - List all runs
- [x] GET /api/runs/{run_id} - Get specific run details
- [x] GET /api/report/{run_id} - JSON report
- [x] GET /api/report/{run_id}/html - HTML report
- [x] GET /api/datasets - List all datasets
- [x] MongoDB indexes on runs.created_at, dq_results.run_id, datasets.dataset_id

### Frontend
- [x] Dashboard page with upload zone and demo button
- [x] Run History page with all previous runs
- [x] Run Details page with expandable rule results
- [x] JSON/HTML report download buttons
- [x] Light theme with Chivo + Inter fonts
- [x] Shadcn UI components (Card, Button, Progress, Collapsible)
- [x] Sonner for toast notifications

### DQ Rules Implemented
1. [x] Null Rate Check - configurable threshold
2. [x] Duplicate Row Detection
3. [x] Unique Key Check (ID columns)
4. [x] Numeric Range Validation
5. [x] Email Regex Validation
6. [x] Phone/ZIP Regex Validation
7. [x] Date Parse Validation (no future dates)
8. [x] Categorical Values Validation
9. [x] Row Count Anomaly Detection (±30%)
10. [x] Outlier Detection (IQR method)

## Prioritized Backlog

### P0 (Completed)
- All core features implemented and tested

### P1 (Future Enhancements)
- [ ] Custom rule configuration UI
- [ ] Bulk file upload
- [ ] Data profiling statistics
- [ ] Rule severity levels (warning vs error)

### P2 (Nice to Have)
- [ ] Scheduled automated runs
- [ ] Email notifications for failures
- [ ] API key authentication
- [ ] Multi-user support with roles

## Next Tasks
1. Add data profiling statistics (column distributions, value counts)
2. Implement custom threshold configuration per rule
3. Add CSV export of failed rows
4. Create comparison view between runs
