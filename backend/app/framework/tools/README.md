# Tools — Catalogue & Documentation

> Auto-discovered tools exposing CRUD operations on files and data formats.
> Each tool is a Python class extending `BaseTool` and is automatically registered at startup.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tools` | Full catalog with schemas and examples |
| `GET` | `/api/tools/categories` | Available categories |
| `GET` | `/api/tools/{slug}` | Tool detail (input/output schemas, examples) |
| `GET` | `/api/tools/{slug}/health` | Health check for a specific tool |
| `GET` | `/api/tools/health` | Health check for all tools |
| `POST` | `/api/tools/{slug}/execute` | Execute a tool |

**Swagger UI**: Available at `/docs` when the backend is running.

## Built-in Tools

### Data Category

| Slug | Name | File | Description |
|------|------|------|-------------|
| `csv-crud` | CSV CRUD | `csv_crud.py` | Create, read, update, delete CSV files |
| `json-crud` | JSON CRUD | `json_crud.py` | Create, read, update, delete JSON files |
| `yaml-crud` | YAML CRUD | `yaml_crud.py` | Create, read, update, delete YAML files |

### File Category

| Slug | Name | File | Description |
|------|------|------|-------------|
| `excel-crud` | Excel CRUD | `excel_crud.py` | Create, read, update, delete XLSX files |
| `pdf-crud` | PDF CRUD | `pdf_crud.py` | Create, read, update, delete PDF files |
| `powerpoint-crud` | PowerPoint CRUD | `powerpoint_crud.py` | Create, read, update, delete PPTX files |
| `word-crud` | Word CRUD | `word_crud.py` | Create, read, update, delete DOCX files |
| `visio-crud` | Visio CRUD | `visio_crud.py` | Create, read, update, delete VSDX files |

### Media Category

| Slug | Name | File | Description |
|------|------|------|-------------|
| `svg-crud` | SVG CRUD | `svg_crud.py` | Create, read, update, delete SVG files |

## Tool Architecture

Each tool follows this structure:

```python
class MyTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            slug="my-tool",
            name="My Tool",
            description="What it does",
            version="1.0.0",
            category="data",
            execution_mode=ToolExecutionMode.SYNC,
            timeout_seconds=30,
            input_schema=[...],
            output_schema=[...],
            examples=[...],
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        # Pure logic - no direct network calls, no filesystem access
        return self.success({"key": "value"})
```

## Common Actions

All CRUD tools support 4 standard actions via the `action` parameter:

| Action | Description | Required Params |
|--------|-------------|-----------------|
| `create` | Generate a file from structured data | `storage_key`, `data` |
| `read` | Parse a file and return structured data | `storage_key` |
| `update` | Modify an existing file | `storage_key`, `data` |
| `delete` | Delete a file from storage | `storage_key` |

## Execution Example

```bash
# List all tools
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/tools

# Get tool detail
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/tools/csv-crud

# Execute a tool
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"params":{"action":"create","storage_key":"data/test.csv","data":{"headers":["name","email"],"rows":[["Alice","alice@mail.com"]]}}}' \
     http://localhost:8000/api/tools/csv-crud/execute
```

## Testing

Each tool can be tested using the `ToolTestCase` base class:

```python
from app.framework.testing import ToolTestCase
from app.framework.tools.csv_crud import CsvCrud

class TestCsvCrud(ToolTestCase):
    tool_class = CsvCrud

    async def test_create(self):
        ctx = self.create_context()
        result = await self.tool.execute({
            "action": "create",
            "storage_key": "test.csv",
            "data": {"headers": ["a"], "rows": [["1"]]},
        }, ctx)
        self.assert_success(result)
        self.assert_storage_put(ctx, "test.csv")
```

## Adding a New Tool

1. Create a file in this directory: `my_tool.py`
2. Implement a class extending `BaseTool`
3. Restart the backend — auto-discovery handles the rest

Or use the CLI generator:
```bash
python -m app.framework.tools.generator my-tool "My Tool" "Description" category
```

See [TOOL_FRAMEWORK.md](../../../../TOOL_FRAMEWORK.md) for the complete guide.
