# PR Review Agent

## Description

An intelligent multi-agent code review system that provides comprehensive automated analysis of GitHub Pull Requests. The system employs specialized AI agents to analyze code changes across multiple dimensions including logic, security, performance, readability, and testing quality.

## Features

- **Multi-Agent Analysis**: Five specialized agents working in parallel
  - **Logic Agent**: Analyzes code correctness, edge cases, and algorithmic efficiency
  - **Security Agent**: Identifies vulnerabilities, injection risks, and security best practices
  - **Performance Agent**: Detects bottlenecks, inefficient algorithms, and optimization opportunities
  - **Readability Agent**: Evaluates code style, naming conventions, and documentation
  - **Testing Agent**: Assesses test coverage, quality, and completeness

- **Flexible Input Methods**:
  - Direct GitHub PR URL integration
  - Manual diff content submission
  - Asynchronous processing for large PRs

- **Comprehensive Reporting**:
  - Overall approval status (APPROVED/COMMENTED/CHANGES_REQUESTED)
  - Category-wise issue summary
  - Critical blockers identification
  - Priority action recommendations
  - Detailed agent-specific analyses

- **Export Capabilities**:
  - PDF report generation with professional formatting
  - JSON export for integration with other tools
  - LLM-formatted markdown reports

## Technologies Used

### Backend
- **FastAPI** - Modern Python web framework
- **LangChain** - LLM orchestration and prompt management
- **OpenRouter** - LLM API integration
- **Pydantic** - Data validation and serialization
- **ReportLab** - PDF generation
- **Python 3.9+**

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type-safe development
- **Vite** - Build tool
- **shadcn/ui** - Component library
- **TailwindCSS** - Styling

## API Endpoints

### Core Endpoints

- `GET /` - Health check and service information
- `POST /review` - Synchronous PR review
- `POST /review/async` - Asynchronous PR review (returns job_id)
- `GET /review/status/{job_id}` - Check async review status
- `POST /generate-pdf` - Generate PDF report from review data
- `POST /format-review` - Format review with LLM for readability
- `POST /parse-diff` - Parse git diff content

### Debug Endpoints

- `POST /review/debug` - Debug request parsing
- `POST /review/test` - Test endpoint with manual validation
- `GET /health` - Detailed health check

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 16+ (for frontend)
- OpenRouter API key
- GitHub token (optional, for higher rate limits)

### Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "OPENROUTER_API_KEY=your_key_here" > .env
echo "GITHUB_TOKEN=your_github_token" >> .env  # Optional

# Run the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Usage Examples

### Review a GitHub PR

```bash
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://github.com/owner/repo/pull/123"}'
```

### Review with Direct Diff

```bash
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{"diff_content": "diff --git a/file.py b/file.py\n..."}'
```

### Generate PDF Report

```bash
curl -X POST http://localhost:8000/generate-pdf \
  -H "Content-Type: application/json" \
  -d @review_result.json \
  --output report.pdf
```

## Project Structure

```
PR_review/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── orchestrator.py      # Multi-agent orchestration
│   ├── agents.py            # Individual agent implementations
│   ├── github_client.py     # GitHub API integration
│   ├── diff_parser.py       # Git diff parsing
│   ├── models.py            # Pydantic models
│   ├── custom_wrapper.py    # LLM wrapper
│   └── rev.py               # PDF generation
├── frontend/
│   └── src/                 # React application
└── README.md
```

## Agent Details

### Logic Analysis Agent
- Identifies logical errors and edge cases
- Analyzes algorithmic correctness
- Detects potential runtime errors
- Evaluates error handling

### Security Analysis Agent
- Scans for common vulnerabilities (SQL injection, XSS, etc.)
- Checks authentication and authorization
- Identifies sensitive data exposure
- Reviews cryptographic implementations

### Performance Analysis Agent
- Detects algorithmic inefficiencies
- Identifies database query issues
- Analyzes memory usage patterns
- Suggests optimization opportunities

### Readability Analysis Agent
- Evaluates code style and conventions
- Checks naming consistency
- Assesses documentation quality
- Reviews code organization

### Testing Analysis Agent
- Analyzes test coverage
- Evaluates test quality and assertions
- Identifies missing test cases
- Reviews test organization

## Response Format

```json
{
  "pr_metadata": {
    "pr_number": 123,
    "title": "Add new feature",
    "author": "username",
    "files_changed": 5
  },
  "review": {
    "approval_status": "CHANGES_REQUESTED",
    "overall_assessment": "...",
    "summary_by_category": {
      "logic": 3,
      "security": 1,
      "performance": 2
    },
    "critical_blockers": [...],
    "priority_actions": [...]
  },
  "agent_analyses": {
    "logic": [...],
    "security": [...],
    "performance": [...],
    "readability": [...],
    "testing": [...]
  },
  "processing_time": 12.34
}
```

## License

This project is licensed under the terms specified in the LICENSE file.
