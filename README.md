# AI Agent - Text-to-SQL and Document RAG

Intelligent agent system for Text-to-SQL and Document RAG capabilities, built with Django Ninja, LangGraph, and Vanna.

## Features

- **Text-to-SQL**: Natural language to SQL conversion using Vanna framework
- **Document RAG**: Semantic search and retrieval from property brochures
- **Intelligent Routing**: LangGraph agent routes queries to appropriate tool
- **RESTful API**: Django Ninja API with JWT authentication
- **Document Ingestion**: Upload and process PDF brochures

## Architecture

- **Framework**: Django Ninja (preferred framework)
- **Agent Orchestration**: LangGraph
- **Database**: SQLite (can be switched to PostgreSQL)
- **Vector Store**: ChromaDB (for both Vanna training and brochure embeddings)
- **LLM**: OpenAI GPT-4o-mini
- **Text-to-SQL**: Vanna framework with ChromaDB backend
- **Embeddings**: OpenAI text-embedding-3-small

## Setup

### Prerequisites

- Python 3.11+
- OpenAI API key

### Installation

1. Clone the repository and navigate to the project directory:
```bash
cd ai-agent
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Load CRM data:
```bash
python manage.py load_leads "../data/Mock CRM leads for nurturing.xlsx"
```

7. Run the server:
```bash
python manage.py runserver
```

## API Endpoints

### Authentication

**POST** `/api/auth/login`
- Request: `{"username": "admin", "password": "admin123"}`
- Response: `{"access_token": "...", "token_type": "bearer"}`

### Agent Query

**POST** `/api/query` (Requires JWT)
- Headers: `Authorization: Bearer <token>`
- Request: `{"query": "How many leads are there?"}`
- Response: `{"response": "...", "task_type": "t2sql", "metadata": {...}}`

### Document Upload

**POST** `/api/documents/upload` (Requires JWT)
- Headers: `Authorization: Bearer <token>`
- Request: Multipart form with `file` field (PDF)
- Response: `{"message": "...", "document_id": "...", "chunks_created": 24}`

**GET** `/api/documents/list` (Requires JWT)
- Response: `{"documents_count": 0, "collection_name": "brochures"}`

## Testing

### Run Pytest Tests

```bash
pytest tests/ -v
```

### Run DeepEval Evaluation

```bash
python tests/run_eval.py
```

This will generate `agent_evaluation_scores.json` with evaluation results.

## Project Structure

```
ai-agent/
├── app/                    # Django project settings
├── api/                    # API endpoints
│   ├── auth.py            # JWT authentication
│   ├── query.py           # Agent query endpoint
│   └── documents.py        # Document ingestion
├── agent/                  # LangGraph agent
│   ├── graph.py           # Agent graph definition
│   ├── nodes.py           # Agent nodes
│   ├── router.py          # Query router
│   └── tools/             # Agent tools
│       ├── t2sql_tool.py  # Text-to-SQL tool
│       └── rag_tool.py    # Document RAG tool
├── crm/                    # CRM models and management
│   ├── models.py          # Lead model
│   └── management/        # Management commands
├── data/                   # Data processing
│   └── ingestion/         # Document ingestion
├── vanna_config/           # Vanna Text-to-SQL setup
├── tests/                  # Test suite
│   ├── test_*.py          # Pytest tests
│   └── run_eval.py        # DeepEval evaluation
└── requirements.txt        # Dependencies
```

## Usage Examples

### Text-to-SQL Queries

- "How many leads are there?"
- "Show me all leads from Lumina Grand"
- "Find leads with budget above 1 million"
- "Count leads by project name"

### Document RAG Queries

- "What are the amenities in Lumina Grand?"
- "Tell me about Sobha Crest features"
- "What facilities are available in DAMAC Bay by Cavalli?"

## Evaluation

The system uses DeepEval for agent performance evaluation. Evaluation results are saved to `agent_evaluation_scores.json` and include:

- Answer Relevancy scores
- Faithfulness metrics (for RAG queries)
- Task type classification accuracy

## Development

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_models.py -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

### Code Quality

The project follows:
- Clean Architecture principles
- OOP design patterns
- RESTful API best practices
- Comprehensive error handling

## License

This project demonstrates an intelligent agent system with Text-to-SQL and Document RAG capabilities.

