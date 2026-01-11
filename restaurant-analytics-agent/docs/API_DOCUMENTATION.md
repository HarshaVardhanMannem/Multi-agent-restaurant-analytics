# Restaurant Analytics Agent API Documentation

Complete API reference with examples for all endpoints in the Restaurant Analytics Agent.

**Base URL:** `http://localhost:8000`

**API Version:** 1.0.0

---

## Table of Contents

1. [Query Endpoints](#query-endpoints)
   - [Process Query](#post-apiquery)
   - [Get Visualization](#get-apivisualizationquery_id)
   - [Explain Query](#post-apiexplain)
   - [Validate SQL](#post-apivalidate-sql)
2. [Schema & Examples](#schema--examples)
   - [Get Schema](#get-apischema)
   - [Get Examples](#get-apiexamples)
3. [Health & Monitoring](#health--monitoring)
   - [Health Check](#get-apihealth)
   - [Get Stats](#get-apistats)
4. [Authentication Endpoints](#authentication-endpoints)
   - [Register](#post-apiauthregister)
   - [Login](#post-apiauthlogin)
   - [Get Current User](#get-apiauthme)
   - [Get Query History](#get-apiauthhistory)
   - [Get Query History for Widgets](#get-apiauthhistorywidgets)
   - [Get Query Detail](#get-apiauthhistoryquery_id)
   - [Delete Query](#delete-apiauthhistoryquery_id)

---

## Query Endpoints

### POST `/api/query`

Process a natural language query about restaurant data. The agent converts your question into SQL, executes it, and returns results with optional visualization.

**Authentication:** Optional (if provided, query is saved to history)

**Request Body:**

```json
{
  "query": "What were total sales on January 2nd?",
  "context": null,
  "include_chart": true,
  "max_results": 100,
  "stream_answer": false
}
```

**Request Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Natural language query (3-1000 characters) |
| `context` | array | No | null | Previous conversation context for follow-up queries |
| `include_chart` | boolean | No | true | Whether to include chart configuration |
| `max_results` | integer | No | 100 | Maximum number of result rows (1-1000) |
| `stream_answer` | boolean | No | false | Stream response progressively (results → answer → visualization) |

**Response (Success):**

```json
{
  "success": true,
  "query_id": "550e8400-e29b-41d4-a716-446655440000",
  "intent": "sales_analysis",
  "sql": "SELECT SUM(total_amount_cents / 100.0) AS total_sales FROM unified_orders WHERE DATE(order_date) = '2025-01-02' AND voided = FALSE",
  "explanation": "This query retrieves the total sales amount for January 2nd, 2025 by summing all non-voided orders from that date.",
  "results": [
    {
      "total_sales": 1234.56
    }
  ],
  "result_count": 1,
  "columns": ["total_sales"],
  "visualization": {
    "type": "table",
    "config": {
      "title": "Total Sales on January 2nd",
      "x_axis": "total_sales",
      "y_axis": null,
      "format_type": "currency",
      "show_values": true
    },
    "chart_js_config": {
      "type": "table",
      "data": {
        "columns": ["total_sales"],
        "rows": [{"total_sales": 1234.56}]
      },
      "options": {
        "title": "Total Sales on January 2nd"
      }
    }
  },
  "execution_time_ms": 45.2,
  "total_processing_time_ms": 1250.8,
  "answer": "Total sales on January 2nd, 2025 were $1,234.56."
}
```

**Response (Clarification Needed):**

```json
{
  "success": true,
  "clarification_needed": true,
  "question": "Which location are you interested in?",
  "suggestions": [
    "What time period are you interested in?",
    "Which location do you want to analyze?",
    "Do you want total sales or a breakdown?"
  ],
  "original_query": "Show me sales",
  "detected_intent": "sales_analysis"
}
```

**Response (Error):**

```json
{
  "success": false,
  "error_code": "SQL_GENERATION_FAILED",
  "error_message": "I couldn't understand your question. Could you try rephrasing it?",
  "details": {},
  "suggestions": [
    "Try asking your question more clearly",
    "Be more specific about what data you want to see",
    "Check example queries for guidance"
  ]
}
```

**cURL Example:**

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "query": "What were total sales on January 2nd?",
    "include_chart": true,
    "max_results": 100
  }'
```

**JavaScript Example:**

```javascript
const response = await fetch('http://localhost:8000/api/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    query: "What were total sales on January 2nd?",
    include_chart: true,
    max_results: 100
  })
});

const data = await response.json();
console.log(data);
```

**Streaming Mode (`stream_answer: true`):**

When streaming is enabled, the API returns Server-Sent Events (SSE) instead of a JSON response. Events are sent in this order:

1. **Results Event** - SQL results immediately after execution
2. **Answer Chunks** - Natural language answer in chunks (for long answers)
3. **Visualization Available Event** - Notification that visualization is being generated
4. **Complete Event** - Final response with all data

**JavaScript Streaming Example:**

```javascript
const response = await fetch('http://localhost:8000/api/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    query: "What were total sales on January 2nd?",
    stream_answer: true
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      
      switch (data.type) {
        case 'results':
          console.log('Results:', data.data);
          break;
        case 'answer_chunk':
          console.log('Answer chunk:', data.chunk);
          break;
        case 'visualization_available':
          console.log('Visualization status:', data.data.status);
          // Fetch visualization when ready
          if (data.data.status === 'ready') {
            fetch(`/api/visualization/${data.data.query_id}`);
          }
          break;
        case 'complete':
          console.log('Complete:', data.response);
          break;
        case 'error':
          console.error('Error:', data.error);
          break;
      }
    }
  }
}
```

---

### GET `/api/visualization/{query_id}`

Fetch precomputed visualization for a query. Used when streaming mode is enabled and visualization is generated asynchronously.

**Authentication:** Not required

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query_id` | string | UUID of the query |

**Response (Success - 200):**

```json
{
  "type": "bar_chart",
  "config": {
    "title": "Top 10 Products",
    "x_axis": "product_name",
    "y_axis": "total_revenue",
    "format_type": "currency",
    "show_values": true
  },
  "chart_js_config": {
    "type": "bar",
    "data": {
      "labels": ["Product A", "Product B", "Product C"],
      "datasets": [{
        "label": "Revenue",
        "data": [1234.56, 987.65, 876.54],
        "backgroundColor": "#4f46e5"
      }]
    },
    "options": {
      "responsive": true,
      "plugins": {
        "title": {
          "display": true,
          "text": "Top 10 Products"
        }
      }
    }
  }
}
```

**Response (Pending - 202):**

```json
{
  "success": false,
  "error_code": "VISUALIZATION_PENDING",
  "error_message": "Visualization is still being generated",
  "status": "pending"
}
```

**Response (Not Applicable - 404):**

```json
{
  "success": false,
  "error_code": "VISUALIZATION_NOT_APPLICABLE",
  "error_message": "A chart isn't available for this type of data"
}
```

**cURL Example:**

```bash
curl http://localhost:8000/api/visualization/550e8400-e29b-41d4-a716-446655440000
```

---

### POST `/api/explain`

Get an explanation of what SQL would be generated for a query without executing it. Useful for debugging and understanding how the agent interprets queries.

**Authentication:** Not required

**Request Body:**

```json
{
  "query": "What were total sales yesterday?",
  "context": null
}
```

**Response:**

```json
{
  "intent": "sales_analysis",
  "entities": {
    "time_range": {
      "type": "relative",
      "value": "yesterday"
    }
  },
  "time_range": {
    "start": "2025-01-03",
    "end": "2025-01-03"
  },
  "tables": ["unified_orders"],
  "sql": "SELECT SUM(total_amount_cents / 100.0) AS total_sales FROM unified_orders WHERE DATE(order_date) = '2025-01-03' AND voided = FALSE",
  "explanation": "This query retrieves the total sales for yesterday by summing all non-voided orders from that date.",
  "visualization_type": "table",
  "validation_passed": true,
  "errors": [],
  "warnings": []
}
```

**cURL Example:**

```bash
curl -X POST http://localhost:8000/api/explain \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What were total sales yesterday?"
  }'
```

---

### POST `/api/validate-sql`

Validate a SQL query without executing it. Checks for safety and correctness.

**Authentication:** Not required

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sql` | string | Yes | SQL query to validate |

**Response:**

```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

**Response (Invalid):**

```json
{
  "valid": false,
  "errors": [
    "Query contains dangerous operation: DROP TABLE",
    "Missing required filter: voided = FALSE"
  ],
  "warnings": [
    "No LIMIT clause - query may return many rows"
  ]
}
```

**cURL Example:**

```bash
curl -X POST "http://localhost:8000/api/validate-sql?sql=SELECT * FROM unified_orders"
```

---

## Schema & Examples

### GET `/api/schema`

Get schema information for the restaurant database. Returns details about tables, views, columns, and important rules.

**Authentication:** Not required

**Response:**

```json
{
  "tables": {
    "unified_orders": {
      "columns": {
        "order_id": "UUID",
        "order_date": "TIMESTAMP",
        "total_amount_cents": "INTEGER",
        "voided": "BOOLEAN"
      },
      "description": "Main order data (money in cents)"
    },
    "unified_order_items": {
      "columns": {
        "item_id": "UUID",
        "order_id": "UUID",
        "product_id": "UUID",
        "quantity": "INTEGER",
        "price_cents": "INTEGER"
      },
      "description": "Line items (money in cents)"
    }
  },
  "views": {
    "v_daily_sales_summary": {
      "columns": {
        "date": "DATE",
        "total_revenue": "DECIMAL",
        "order_count": "INTEGER"
      },
      "description": "Daily metrics (money in dollars)",
      "type": "view"
    }
  },
  "important_rules": [
    "Base tables: Divide *_cents by 100.0 for dollars",
    "Views: Already in dollars, don't divide",
    "Always filter voided = FALSE on unified_orders",
    "Prefer views for aggregations (faster)"
  ]
}
```

**cURL Example:**

```bash
curl http://localhost:8000/api/schema
```

---

### GET `/api/examples`

Get example natural language queries that demonstrate what kinds of questions can be asked.

**Authentication:** Not required

**Response:**

```json
{
  "examples": [
    {
      "query": "What were total sales on January 2nd?",
      "intent": "sales_analysis",
      "description": "Get aggregate sales for a specific day"
    },
    {
      "query": "Show me the top 10 selling products",
      "intent": "product_analysis",
      "description": "Product ranking by sales volume"
    },
    {
      "query": "Compare revenue across all locations",
      "intent": "location_comparison",
      "description": "Location-wise revenue comparison"
    },
    {
      "query": "What are our busiest hours?",
      "intent": "time_series",
      "description": "Time-of-day analysis for staffing"
    },
    {
      "query": "Payment method breakdown",
      "intent": "payment_analysis",
      "description": "Analyze payment type distribution"
    }
  ]
}
```

**cURL Example:**

```bash
curl http://localhost:8000/api/examples
```

---

## Health & Monitoring

### GET `/api/health`

Health check endpoint to verify API and database connectivity.

**Authentication:** Not required

**Response:**

```json
{
  "status": "healthy",
  "database_connected": true,
  "version": "1.0.0"
}
```

**Response (Degraded):**

```json
{
  "status": "degraded",
  "database_connected": false,
  "version": "1.0.0"
}
```

**cURL Example:**

```bash
curl http://localhost:8000/api/health
```

---

### GET `/api/stats`

Get API statistics including database connection pool information.

**Authentication:** Not required

**Response:**

```json
{
  "database": {
    "pool_size": 10,
    "idle_connections": 3,
    "active_connections": 2
  },
  "agent": {
    "status": "ready"
  }
}
```

**cURL Example:**

```bash
curl http://localhost:8000/api/stats
```

---

## Authentication Endpoints

All authentication endpoints are prefixed with `/api/auth`.

### POST `/api/auth/register`

Register a new user account.

**Authentication:** Not required

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Response (201 Created):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "user",
    "is_active": true,
    "created_at": "2025-01-01T12:00:00Z"
  }
}
```

**cURL Example:**

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "John Doe"
  }'
```

---

### POST `/api/auth/login`

Authenticate user and receive JWT token.

**Authentication:** Not required

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "user",
    "is_active": true,
    "created_at": "2025-01-01T12:00:00Z"
  }
}
```

**Response (401 Unauthorized):**

```json
{
  "detail": "Invalid email or password"
}
```

**cURL Example:**

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

---

### GET `/api/auth/me`

Get current authenticated user information.

**Authentication:** Required (Bearer token)

**Headers:**

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Response (200 OK):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "user",
  "is_active": true,
  "created_at": "2025-01-01T12:00:00Z"
}
```

**cURL Example:**

```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### GET `/api/auth/history`

Get query history for the current user.

**Authentication:** Required (Bearer token)

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 50 | Maximum number of queries to return (max 100) |
| `offset` | integer | No | 0 | Number of queries to skip |

**Response (200 OK):**

```json
[
  {
    "query_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "660e8400-e29b-41d4-a716-446655440001",
    "natural_query": "What were total sales on January 2nd?",
    "generated_sql": "SELECT SUM(...)",
    "intent": "sales_analysis",
    "execution_time_ms": 45.2,
    "result_count": 1,
    "success": true,
    "created_at": "2025-01-01T12:00:00Z"
  }
]
```

**cURL Example:**

```bash
curl http://localhost:8000/api/auth/history?limit=10&offset=0 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### GET `/api/auth/history/widgets`

Get query history with full results for restoring widgets. Returns detailed data including `results_sample`, `columns`, and `visualization_config`.

**Authentication:** Required (Bearer token)

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 20 | Maximum number of queries to return (max 50) |

**Response (200 OK):**

```json
[
  {
    "query_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "660e8400-e29b-41d4-a716-446655440001",
    "natural_query": "What were total sales on January 2nd?",
    "generated_sql": "SELECT SUM(...)",
    "intent": "sales_analysis",
    "execution_time_ms": 45.2,
    "result_count": 1,
    "results_sample": [
      {
        "total_sales": 1234.56
      }
    ],
    "columns": ["total_sales"],
    "visualization_type": "table",
    "visualization_config": {
      "title": "Total Sales on January 2nd",
      "x_axis": "total_sales"
    },
    "answer": "Total sales on January 2nd, 2025 were $1,234.56.",
    "success": true,
    "created_at": "2025-01-01T12:00:00Z"
  }
]
```

**cURL Example:**

```bash
curl http://localhost:8000/api/auth/history/widgets?limit=20 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### GET `/api/auth/history/{query_id}`

Get detailed information about a specific query.

**Authentication:** Required (Bearer token)

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query_id` | string | UUID of the query |

**Response (200 OK):**

```json
{
  "query_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "660e8400-e29b-41d4-a716-446655440001",
  "natural_query": "What were total sales on January 2nd?",
  "generated_sql": "SELECT SUM(total_amount_cents / 100.0) AS total_sales FROM unified_orders WHERE DATE(order_date) = '2025-01-02' AND voided = FALSE",
  "intent": "sales_analysis",
  "execution_time_ms": 45.2,
  "result_count": 1,
  "results_sample": [
    {
      "total_sales": 1234.56
    }
  ],
  "columns": ["total_sales"],
  "visualization_type": "table",
  "visualization_config": {
    "title": "Total Sales on January 2nd",
    "x_axis": "total_sales"
  },
  "answer": "Total sales on January 2nd, 2025 were $1,234.56.",
  "success": true,
  "error_message": null,
  "created_at": "2025-01-01T12:00:00Z"
}
```

**cURL Example:**

```bash
curl http://localhost:8000/api/auth/history/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### DELETE `/api/auth/history/{query_id}`

Delete a query from history.

**Authentication:** Required (Bearer token)

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query_id` | string | UUID of the query |

**Response (204 No Content):**

Empty response body

**Response (404 Not Found):**

```json
{
  "detail": "Query not found or access denied"
}
```

**cURL Example:**

```bash
curl -X DELETE http://localhost:8000/api/auth/history/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "success": false,
  "error_code": "ERROR_CODE",
  "error_message": "Human-readable error message",
  "details": {
    "additional": "error information"
  },
  "suggestions": [
    "Suggestion 1",
    "Suggestion 2"
  ]
}
```

### Common Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `SQL_GENERATION_FAILED` | 200 | Could not generate valid SQL from query |
| `SQL_EXECUTION_FAILED` | 200 | SQL query execution failed |
| `QUERY_TIMEOUT` | 200 | Query execution exceeded timeout |
| `QUERY_CANCELLED` | 200 | Query was cancelled (e.g., during shutdown) |
| `NO_SQL_GENERATED` | 200 | No SQL was generated for the query |
| `VISUALIZATION_NOT_APPLICABLE` | 404 | Chart not available for this data type |
| `VISUALIZATION_PENDING` | 202 | Visualization still being generated |
| `VISUALIZATION_ERROR` | 500 | Error generating visualization |
| `HTTP_401` | 401 | Unauthorized - invalid or missing token |
| `HTTP_403` | 403 | Forbidden - insufficient permissions |
| `HTTP_404` | 404 | Resource not found |
| `HTTP_500` | 500 | Internal server error |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## Authentication

Most endpoints support optional authentication. When provided, queries are saved to the user's history.

**Header Format:**

```
Authorization: Bearer <access_token>
```

**Getting a Token:**

1. Register a new account: `POST /api/auth/register`
2. Login: `POST /api/auth/login`

Both endpoints return an `access_token` that should be included in subsequent requests.

**Token Expiration:**

Tokens expire after 24 hours (86400 seconds). Refresh by logging in again.

---

## Rate Limiting

Currently, no rate limiting is enforced. Consider implementing rate limiting for production use.

---

## Interactive API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

These interactive docs allow you to:
- Browse all endpoints
- Test API calls directly in the browser
- View request/response schemas
- See example requests

---

## Best Practices

1. **Use Context for Follow-up Queries:**
   ```json
   {
     "query": "What about last week?",
     "context": [
       {"role": "user", "content": "What were total sales yesterday?"},
       {"role": "assistant", "content": "Total sales yesterday were $1,234.56."}
     ]
   }
   ```

2. **Enable Streaming for Better UX:**
   Set `stream_answer: true` to get results faster and show progress to users.

3. **Handle Errors Gracefully:**
   Always check the `success` field and handle errors appropriately.

4. **Store Query IDs:**
   Save `query_id` from responses to fetch visualizations later or track query history.

5. **Use Appropriate Limits:**
   Set `max_results` based on your UI needs (default: 100, max: 1000).

---

## Support

For issues or questions:
- Check the [README.md](../README.md) for setup instructions
- Review example queries: `GET /api/examples`
- Check schema information: `GET /api/schema`

