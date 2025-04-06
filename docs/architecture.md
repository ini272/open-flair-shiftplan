# Application Architecture

## Overview

This document describes the architecture of our FastAPI application with OpenTelemetry tracing and token-based authentication.

## Component Diagram

```mermaid
graph TD
    Client[Client] -->|HTTP Request| FastAPI[FastAPI App]
    FastAPI -->|Middleware| Tracing[OpenTelemetry Tracing]
    FastAPI -->|Route| UserRouter[User Router]
    FastAPI -->|Route| AuthRouter[Auth Router]
    FastAPI -->|Route| ProtectedRouter[Protected Router]
    UserRouter -->|CRUD Operations| UserCRUD[User CRUD]
    AuthRouter -->|CRUD Operations| TokenCRUD[Token CRUD]
    ProtectedRouter -->|Requires| AuthDep[Auth Dependency]
    UserCRUD -->|Database Access| SQLAlchemy[SQLAlchemy ORM]
    TokenCRUD -->|Database Access| SQLAlchemy
    SQLAlchemy -->|SQL Queries| Database[(SQLite Database)]
    Tracing -->|Export Spans| Jaeger[Jaeger UI]
```

## Request Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Router
    participant CRUD
    participant DB as Database
    participant Jaeger
    
    Client->>FastAPI: HTTP Request
    FastAPI->>Jaeger: Start Request Span
    FastAPI->>Router: Route to Handler
    Router->>Jaeger: Start Operation Span
    Router->>CRUD: Call CRUD Method
    CRUD->>DB: Database Query
    DB->>CRUD: Query Result
    CRUD->>Router: Return Data
    Router->>Jaeger: End Operation Span
    Router->>FastAPI: Return Response
    FastAPI->>Jaeger: End Request Span
    FastAPI->>Client: HTTP Response
```

## Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant AuthRouter
    participant TokenCRUD
    participant DB as Database
    
    Client->>AuthRouter: GET /auth/login/{token}
    AuthRouter->>TokenCRUD: Validate Token
    TokenCRUD->>DB: Query Token
    DB->>TokenCRUD: Token Data
    TokenCRUD->>AuthRouter: Token Valid/Invalid
    
    alt Token Valid
        AuthRouter->>Client: Set Cookie & 200 OK
    else Token Invalid
        AuthRouter->>Client: 401 Unauthorized
    end
    
    Client->>ProtectedRouter: Request Protected Resource
    ProtectedRouter->>AuthDep: Check Authentication
    AuthDep->>TokenCRUD: Validate Token from Cookie
    TokenCRUD->>DB: Query Token
    DB->>TokenCRUD: Token Data
    TokenCRUD->>AuthDep: Token Valid/Invalid
    
    alt Token Valid
        AuthDep->>ProtectedRouter: Allow Request
        ProtectedRouter->>Client: Protected Resource
    else Token Invalid
        AuthDep->>Client: 401 Unauthorized
    end
```

## Debuggability and Observability

Our application is designed with debuggability and observability as core principles, ensuring issues can be quickly identified and resolved.

### Testing Strategy

```mermaid
graph TD
    A[Test Types] --> B[Unit Tests]
    A --> C[Integration Tests]
    A --> D[API Tests]
    
    B --> B1[CRUD Operations]
    B --> B2[Model Validations]
    
    C --> C1[Database Interactions]
    C --> C2[Authentication Flows]
    
    D --> D1[Endpoint Responses]
    D --> D2[Error Handling]
    D --> D3[Authentication/Authorization]
    
    E[Test Infrastructure] --> E1[In-Memory Database]
    E --> E2[Mocked Tracers]
    E --> E3[Test Fixtures]
    E --> E4[Automated CI]
```

Our testing approach ensures code quality and prevents regressions:

- **Test Coverage**: Tests cover all critical paths including user operations, authentication flows, and group management
- **Isolation**: Each test runs with a clean database state
- **Fixtures**: Reusable components provide database sessions, authenticated clients, and test data
- **Mocking**: External dependencies like tracers are mocked to ensure tests are reliable and fast

### Tracing Implementation

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI Endpoint
    participant Handler as Route Handler
    participant CRUD as CRUD Operation
    participant DB as Database
    participant Jaeger as Jaeger UI
    
    Client->>API: HTTP Request
    API->>Jaeger: Create Request Span
    API->>Handler: Route to Handler
    
    Handler->>Jaeger: Create Operation Span
    Handler->>Jaeger: Add Operation Attributes
    
    Handler->>CRUD: Call CRUD Method
    CRUD->>DB: Execute Query
    DB->>CRUD: Return Results
    
    Handler->>Jaeger: Add Result Attributes
    Handler->>Jaeger: Add Events (success/error)
    
    Handler->>API: Return Response
    API->>Jaeger: End Request Span
    API->>Client: HTTP Response
```

Our tracing strategy provides deep visibility into application behavior:

- **Hierarchical Spans**: Each operation creates a span within the request span
- **Rich Attributes**: Spans include query parameters, entity IDs, and result metadata
- **Event Timeline**: Key points in request processing are marked with timestamped events
- **Error Tracking**: Exceptions and error conditions are captured with context
- **Performance Metrics**: Execution times are recorded for performance analysis

### Debugging Workflow

```mermaid
flowchart TD
    A[Issue Reported] --> B{Error or Performance?}
    
    B -->|Error| C[Check Logs]
    B -->|Performance| D[Check Traces]
    
    C --> E[Identify Error Type]
    D --> F[Identify Slow Component]
    
    E --> G[Run Targeted Tests]
    F --> H[Profile Component]
    
    G --> I[Fix and Verify]
    H --> I
    
    I --> J[Add Regression Test]
    J --> K[Deploy Fix]
```

Our debugging workflow is streamlined through:

- **Structured Logging**: Consistent log format with correlation IDs linking to traces
- **Trace Visualization**: Jaeger UI provides timeline views of request processing
- **Test Reproduction**: Issues can be reproduced and verified with targeted tests
- **Middleware Insights**: Request processing times are captured by middleware

### Group Management Visualization

```mermaid
graph TD
    User[User] -->|belongs to| Group[Group]
    Group -->|contains| Users[Multiple Users]
    
    API[API Endpoints] --> CreateG[Create Group]
    API --> ListG[List Groups]
    API --> UpdateG[Update Group]
    API --> DeleteG[Delete Group]
    API --> AddUser[Add User to Group]
    API --> RemoveUser[Remove User from Group]
    
    CreateG --> Validation[Name Uniqueness]
    AddUser --> UserCheck[User Exists]
    AddUser --> GroupCheck[Group Exists]
    RemoveUser --> MembershipCheck[User in Group]
```

The group management system provides:

- **One-to-Many Relationship**: Each user belongs to at most one group
- **Validation Rules**: Enforces unique group names and valid references
- **Flexible Membership**: Users can be added to or removed from groups
- **Soft Deletion**: Groups can be marked inactive without losing data

## Authentication Implementation

The application uses a token-based authentication system:

1. **Access Tokens**: Tokens are created and stored in the database with the following attributes:
   - Name: A human-readable identifier
   - Token: A unique string used for authentication
   - Created At: Timestamp when the token was created
   - Expires At: Optional expiration timestamp
   - Is Active: Boolean indicating if the token is still valid

2. **Login**: Users authenticate by visiting `/auth/login/{token}`, which:
   - Validates the token against the database
   - Sets an HTTP-only cookie with the token value
   - Returns a success message

3. **Session**: Authentication state is maintained via HTTP cookies:
   - The `access_token` cookie contains the token value
   - The cookie is HTTP-only for security
   - The cookie has a configurable expiration

4. **Logout**: Users can logout by visiting `/auth/logout`, which:
   - Clears the `access_token` cookie
   - Returns a success message

5. **Token Management**:
   - Tokens can be created via the `/auth/tokens` endpoint
   - Tokens can be listed via the `/auth/tokens` endpoint
   - Tokens can be invalidated via the `/auth/tokens/{token_id}` endpoint

6. **Authentication Check**: The `/auth/check` endpoint allows clients to verify their authentication status

## Deployment

The application is deployed using Docker Compose with the following services:

1. **FastAPI**: The main application container
2. **Jaeger**: For collecting and visualizing traces

Environment variables and volume mounts are configured to ensure proper communication between services.

## Database Implementation Details

### DateTime Handling

Our application uses SQLite as the database backend, which requires special handling for datetime objects:

1. **Issue**: SQLite's DateTime type only accepts Python datetime objects, not string representations.

2. **Challenge**: When processing API requests, datetime values arrive as strings and need conversion.

3. **Solution**: We implemented a two-part approach:
   - **Schema Validation**: Pydantic validators in schemas (e.g., `ShiftCreate`) convert string datetimes to Python datetime objects
   - **CRUD Method Override**: Custom implementation of the `create` method in `CRUDShift` preserves datetime objects by avoiding `jsonable_encoder`

4. **Implementation Example**:
   ```python
   # In app/schemas/shift.py
   @validator('start_time', 'end_time', pre=True)
   def parse_datetime(cls, value):
       if isinstance(value, str):
           # Convert string to datetime object
           return datetime.fromisoformat(value.replace('Z', '+00:00'))
       return value
   
   # In app/crud/shift.py
   def create(self, db: Session, *, obj_in: ShiftCreate) -> Shift:
       # Direct attribute access preserves datetime objects
       db_obj = Shift(
           title=obj_in.title,
           start_time=obj_in.start_time,  # Remains a datetime object
           end_time=obj_in.end_time,      # Remains a datetime object
           # ...
       )
       # ...
   ```

This approach ensures proper handling of datetime values throughout the application lifecycle, from API request to database storage.
