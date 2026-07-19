# 5. Technology Stack

## 5.1 Frontend

- React
- TypeScript
- React Router or an equivalent routing library
- A typed API client
- Server-Sent Events for live workflow updates
- A charting library for decision packages and request visualizations

## 5.2 Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy 2.0 async
- Alembic
- LangGraph
- LangChain where useful

## 5.3 Data

- Neon hosted PostgreSQL for relational data
- Pinecone hosted vector database for RAG embeddings
- Object storage for uploaded files if needed during implementation

## 5.4 LLM

A hosted LLM API.

Version 1 may use one provider and one shared API key, while department agents use different prompts, tools, schemas, and settings.

The model should remain configurable.

## 5.5 Real-Time

Server-Sent Events provide backend-to-frontend live updates.

Normal HTTP endpoints handle:

- approve;
- reject;
- cancel;
- provide information;
- confirm human action.

## 5.6 Architecture Style

- Feature-based modular monolith
- One FastAPI backend
- One centralized LangGraph graph
- One shared PostgreSQL schema
- One configured Pinecone index with one namespace per company and metadata filters inside each namespace
- Managed hosted infrastructure

## 5.7 Explicitly Avoided in Version 1

Unless later justified:

- microservices;
- multiple relational databases;
- MongoDB;
- Redis;
- Kafka;
- separate department databases;
- separate department LangGraph subgraphs;
- dynamic company-created departments;
- a Tool Selector agent;
- persistent agent memory;
- direct frontend access to data stores or LLMs.
