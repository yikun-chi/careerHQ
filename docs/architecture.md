# Design Documentation 

## 1. Core Design Principles
### 1.1 Hexagonal Architecture (Ports & Adapters)
* **The Core:** Contains the "rules of coaching," the "Turn Pipeline," and the "Profile Schema." It has zero dependencies on specific vendors (OpenAI, AWS, etc.).
* **The Ports:** Interfaces (Protocols) that define how the Core expects to talk to the world (e.g., `LLMProvider`, `ProfileStore`).
* **The Adapters:** Concrete implementations (e.g., `OpenAIAdapter`, `PostgresStore`). 

### 1.2: Major Components 

The system is partitioned into four distinct top-level directories, each representing a specific layer of the application lifecycle.

| Component | What it does |
| :--- | :--- |
| **`apps/`** | **The Engines:** The actual programs that run on the server to handle requests. |
| **`packages/`** | **The Knowledge:** The internal rules, career coaching logic, and database tools. |
| **`web/`** | **The Interface:** Everything the user sees in their browser (Chat & Charts). |
| **`tests/`** | **The Safety Net:** Automated checks to make sure no data gets lost or corrupted. |

## 2. The Apps Layer (`apps/`)
The `apps/` directory contains the two primary services that power the platform. While they share the same "Knowledge" from the `packages/` folder, they perform very different roles in the user experience.

### 2.1 The API Service (`apps/api/`)
This is the **Synchronous Gateway**. It is the only part of the backend that the `web/` interface talks to directly.
* **Authentication & Security:** Verifies user tokens and protects your data.
* **Chat Management:** Receives the user's message and coordinates with the AI to send a text response back immediately.
* **Data Retrieval:** Fetches the current state of the User Profile (all those hundreds of columns) so the frontend can display them.
* **Fast Response:** Optimized for low latency so the user feels they are having a "real-time" conversation.

### 2.2 The Worker Service (`apps/worker/`)
This is the **Asynchronous Processor**. It handles the "thinking" that takes too long for a live chat response.
* **Profile Extraction:** It reviews the chat transcript in the background to find and update the hundreds of specific profile attributes (e.g., updating "Years of Experience" or "Skill Levels").
* **Roadmap Generation:** When a user's goals change, this service does the heavy computation to build or update their career path.
* **Long-Running Tasks:** Handles file uploads (like Resume PDFs) and performs deep analysis that might take several seconds or minutes.
* **Reliability:** If an AI task fails, the worker can automatically retry it without the user ever seeing an error message in their chat window.


## 3. The Packages Layer (`packages/`)

The `packages/` directory contains the shared internal logic of the system. It is structured to separate business rules from technical implementation details.

### 3.1 Core: The Business Logic (`packages/core/`)
The `core` module houses the domain logic and coaching rules. It is designed to be technology-agnostic, having no direct dependencies on databases or external APIs.

* **domain/**: Contains the fundamental entities and data structures. This is where the explicit schema for the **User Profile** (and its hundreds of career attributes) is defined using Python dataclasses or Pydantic models. Each attribute can also include metadata such as `source`, `extracted_at`, and optional `confidence` for provenance.
* **ports/**: Defines the interfaces (Protocols) that the system requires to operate. It establishes the "contract" for external services, such as `ProfileRepository` or `ChatProvider`, without specifying the implementation.
* **use_cases/**: Implements specific application workflows. This includes the "Turn Pipeline" orchestration, which manages the sequence of loading context, generating responses, and scheduling profile updates.
* **policies/**: Contains the logic for different coaching states. These modules determine how the system should pivot between "Information Gathering" (Intake) and "Actionable Feedback" (Coaching).
* **prompts/**: A centralized management system for LLM templates. This allows for versioned, structured instructions that guide the AI's behavior and tone.
* **schemas/**: Defines the data validation layers. These are primarily Pydantic models used to ensure that AI-generated content is correctly formatted before being passed to the domain or database layers.



### 3.2 Infra: The Implementation Layer (`packages/infra/`)
The `infra` module contains the concrete implementations (Adapters) of the interfaces defined in the `core`.

* **llm/**: Provides the technical integration for AI providers. This includes the specific API handling and error-correction logic for vendors like OpenAI or Anthropic.
* **db/**: Manages data persistence. It contains the SQLAlchemy models that map the `core` profile entities to physical PostgreSQL columns, as well as the migration files for schema versioning.
* **queue/**: Handles asynchronous communication. This provides the Celery and Redis configuration required to pass tasks from the API to the background Worker.
* **telemetry/**: Implements observability tools. This includes structured logging, error tracking, and performance metrics for monitoring system health and AI response quality.



## 4. The Web Layer (`web/`)

The `web/` directory contains the client-side application. It is a standalone environment responsible for the user interface, data visualization, and real-time interaction. It communicates with the backend exclusively through the **API Service**.

### 4.1 Frontend Architecture
The frontend is built using a modern component-based framework (e.g., React or Next.js) to manage the complex state of the chat and the career profile.

* **Components/**: Modular UI elements such as the chat interface, profile sidebars, and navigation menus.
* **Visualizations/**: A specialized module for data-driven graphics. It maps the hundreds of profile attributes from the database into visual formats like skill spider charts, career timelines, and progress bars.
* **Services/**: The API client layer that handles HTTP requests to the `apps/api/` endpoints. It ensures that data types in the frontend match the schemas defined in the backend.
* **State Management/**: Handles the local "Source of Truth" for the browser. It ensures that when the AI extracts a new skill in the background, the UI updates the corresponding visualization without a full page reload.



### 4.2 Integration Points
* **Chat Stream:** Uses Server-Sent Events (SSE) or WebSockets to display the AI's response word-by-word, providing a low-latency experience.
* **Profile Synchronization:** Periodically polls or listens for updates from the **Worker Service**. As the attributes are populated in the database, this layer reflects those changes in the user's career roadmap.
* **Visualization Engine:** Uses libraries like D3.js or Recharts to render the high-density data. Because the backend uses explicit columns, the frontend can request specific data points needed for a single chart (e.g., `GET /profile?fields=technical_skills`).
