# AI-Powered Invoice Processing & Approval Dashboard

A full-stack Streamlit application that automates invoice processing using AI-assisted data extraction, SQLite storage, and a multi-stage approval workflow. Built as a portfolio project demonstrating Python development, database design, PDF parsing, API integration, and interactive data visualization.

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Database Design](#database-design)
- [Invoice Processing Workflow](#invoice-processing-workflow)
- [Approval Workflow](#approval-workflow)
- [Screenshots](#screenshots)
- [Future Enhancements](#future-enhancements)
- [Author](#author)

---

## Problem Statement

Manual invoice processing is time-consuming, error-prone, and difficult to scale. Accounts payable teams spend hours reading PDF invoices, typing data into spreadsheets, and routing documents for approval. This leads to delayed payments, missed discounts, and a lack of visibility into outstanding liabilities.

This project solves these problems by providing a centralized dashboard where users can upload PDF invoices, automatically extract key fields using AI, review and edit the data, and route invoices through a structured approval process — all from a single web interface.

---

## Key Features

- **PDF Invoice Upload** — Drag-and-drop upload of one or more PDF invoices with instant text extraction
- **AI-Assisted Extraction** — OpenAI-powered field extraction with automatic fallback to rule-based regex parsing
- **Editable Review Form** — Pre-populated fields that users can review and correct before saving
- **Duplicate Detection** — Prevents saving the same invoice multiple times based on invoice number, vendor, and amount
- **Interactive Dashboard** — Real-time KPI metrics, status distribution charts, and monthly trends
- **Invoice Management** — Full-text search, status filters, vendor filters, and date range filtering
- **Approval Center** — Dedicated workflow for reviewing and processing pending invoices with confirmation dialogs
- **Analytics Page** — Six interactive Plotly charts covering status breakdown, monthly trends, and vendor analysis
- **SQLite Storage** — Lightweight, zero-configuration database with parameterized queries

---

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Streamlit | Interactive web UI with sidebar navigation |
| Charts | Plotly Express | Interactive pie charts, bar charts, and histograms |
| Data | Pandas | Data manipulation, aggregation, and table display |
| PDF Parsing | PyMuPDF | Text extraction from PDF documents |
| AI Extraction | OpenAI API | GPT-powered structured data extraction |
| Database | SQLite | Lightweight relational storage |
| Config | python-dotenv | Environment variable management |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Streamlit UI                      │
│  Dashboard │ Upload │ Management │ Approval │ Stats │
└──────┬──────────┬──────────────┬────────────┬───────┘
       │          │              │            │
       ▼          ▼              ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│database.py│ │extractor │ │ai_extract│ │  Charts  │
│  (SQLite) │ │   .py    │ │   or.py  │ │ (Plotly) │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
                   │              │
                   ▼              ▼
              ┌─────────┐  ┌──────────┐
              │ PyMuPDF  │  │ OpenAI   │
              │ (PDF)    │  │ API      │
              └─────────┘  └──────────┘
```

The application follows a **modular architecture** with clear separation of concerns:

- **`app.py`** — Presentation layer. Handles all Streamlit UI rendering, user interaction, and page routing. Contains no database or extraction logic.
- **`database.py`** — Data access layer. All SQLite operations are encapsulated here with parameterized queries. No SQL appears in any other file.
- **`extractor.py`** — PDF processing layer. Handles PyMuPDF text extraction and rule-based regex field parsing.
- **`ai_extractor.py`** — AI integration layer. Sends extracted text to the OpenAI API and returns structured JSON. Gracefully degrades when unavailable.

---

## Project Structure

```
invoice-automation-app/
│
├── app.py              # Streamlit application — UI, routing, page rendering
├── database.py         # SQLite schema definition and CRUD operations
├── extractor.py        # PDF text extraction and rule-based field parsing
├── ai_extractor.py     # AI-powered invoice field extraction via OpenAI API
│
├── requirements.txt    # Pinned Python dependencies
├── .env.example        # Environment variable template (API keys)
├── .gitignore          # Git ignore rules
├── README.md           # This file
│
├── uploads/            # Storage for uploaded PDF invoice files
└── invoices.db         # SQLite database (auto-created on first run)
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- An OpenAI API key (optional — the app works without it using rule-based extraction)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/invoice-automation-app.git
cd invoice-automation-app
```

### 2. Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy the template
copy .env.example .env       # Windows
cp .env.example .env         # macOS / Linux
```

Open `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

> **Note:** If `OPENAI_API_KEY` is not set, the application automatically falls back to rule-based regex extraction. No functionality is lost.

### 5. Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

---

## Database Design

The application uses a single `invoices` SQLite table with the following schema:

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Auto-incrementing primary key |
| `invoice_number` | TEXT | Extracted invoice number |
| `vendor_name` | TEXT | Vendor or supplier name (required) |
| `invoice_date` | TEXT | Date the invoice was issued |
| `due_date` | TEXT | Payment due date |
| `subtotal` | REAL | Pre-tax subtotal |
| `tax` | REAL | Tax amount |
| `total_amount` | REAL | Final total amount |
| `currency` | TEXT | Currency code (default: USD) |
| `status` | TEXT | Pending, Approved, or Rejected |
| `file_name` | TEXT | Original uploaded filename |
| `extracted_text` | TEXT | Full text extracted from the PDF |
| `created_at` | TEXT | Timestamp when the record was created |
| `updated_at` | TEXT | Timestamp of last status change |

The database file (`invoices.db`) is created automatically on the first application run. No manual setup is required.

---

## Invoice Processing Workflow

```
Upload PDF ──► Extract Text ──► Parse Fields ──► Review & Edit ──► Save to DB
                    │                  │
                    ▼                  ▼
              PyMuPDF text       AI extraction
              extraction         (or rule-based
                                 regex fallback)
```

1. **Upload** — User selects one or more PDF files via the file uploader
2. **Extract** — PyMuPDF reads each page and concatenates the text content
3. **Parse** — The system attempts AI-powered extraction first. If unavailable, it falls back to regex-based parsing
4. **Review** — Extracted fields are pre-populated in an editable form. User can correct any values
5. **Duplicate Check** — The system checks for existing invoices with the same invoice number, vendor, and amount
6. **Save** — Validated data is written to the SQLite database with status set to "Pending"

---

## Approval Workflow

```
Pending ──► Review Details ──► Approve / Reject ──► Status Updated
                                   │
                                   ▼
                          Confirmation dialog
                          prevents accidental actions
```

1. The **Approval Center** displays all invoices with "Pending" status
2. User selects an invoice to view its complete details
3. User clicks **Approve** or **Reject**
4. A confirmation dialog appears to prevent accidental changes
5. On confirmation, the invoice status is updated and the `updated_at` timestamp is set

---

## Screenshots

> Screenshots will be added after the next UI polish pass.

<!-- 
![Dashboard](screenshots/dashboard.png)
![Upload](screenshots/upload.png)
![Management](screenshots/management.png)
![Approval](screenshots/approval.png)
![Analytics](screenshots/analytics.png)
-->

---

## Future Enhancements

- **Authentication** — User login with role-based access control
- **Batch Processing** — Process hundreds of invoices via a background queue
- **Email Integration** — Send approval notifications and invoice copies via email
- **Multi-currency Support** — Automatic currency detection and conversion
- **Line Item Extraction** — Parse individual line items from invoice tables
- **Export to Excel/CSV** — Download filtered invoice data in standard formats
- **Audit Trail** — Log all status changes with timestamps and reviewer information
- **Deployment** — Docker containerization and cloud deployment (AWS/GCP/Azure)

---

## Author

**Your Name**

- GitHub: [yourusername](https://github.com/yourusername)
- LinkedIn: [Your Name](https://linkedin.com/in/yourname)
- Email: your.email@example.com

---

Built as a software development portfolio project.
