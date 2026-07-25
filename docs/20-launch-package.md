# Launch Package — TellUS AI v1.0

## 1. Deployment Checklist

### Infrastructure
- [ ] Neon PostgreSQL production instance provisioned.
- [ ] Pinecone index created with correct dimension (1536) and similarity metric (cosine).
- [ ] Backend deployed to production host (Docker / fly.io / VPS).
- [ ] Frontend built and served from CDN/static host.
- [ ] Environment variables configured (no secrets in repo):
  - `DATABASE_URL`, `SECRET_KEY`, `PINECONE_API_KEY`, `OPENAI_API_KEY`
- [ ] HTTPS enforced for all traffic.
- [ ] CORS whitelist configured for production domain.

### Database
- [ ] Alembic migrations applied to production.
- [ ] Seed script `scripts/seed_demo.py` can be run for demo tenant if desired.

### Monitoring
- [ ] Application logs aggregated (structured JSON).
- [ ] Error alerting configured for 5xx rates > 0.1%.
- [ ] Health endpoint `/health` monitored.

## 2. Known Limitations

| Limitation | Impact | Planned Resolution |
|-----------|--------|-------------------|
| Single centralized LangGraph graph | All traffic routed through one graph instance | v2: Graph federation per department |
| No real-time collaboration editing | Managers cannot edit requests simultaneously | v2: Operational transforms / Yjs |
| Change password does not revoke sessions | Old tokens remain valid until expiry | v2: Token rotation on password change |
| Frontend does not retry SSE on 401 | User may miss updates after token expiry | v2: Reconnect with refreshed token |

## 3. Support Runbook

**Password reset (admin-assisted)**
1. Log into backend shell.
2. Run Python one-liner using `UserRepository` to set new `password_hash`.

**Stuck workflow**
1. Identify request ID from frontend.
2. Check `business_requests.workflow_state` JSON.
3. If terminal failure, update status manually or use admin API.

**Document ingestion failed**
1. Check `knowledge_documents` table for `ingestion_status = failed`.
2. Read `ingestion_error_safe` column for user-facing message.
3. Re-upload or fix file format.

## 4. Post-Launch Iterations
- Week 1: Monitor failure logs, fix immediate bugs.
- Week 2: Gather user feedback on routing accuracy.
- Month 1: Begin planning v2 department-specific subgraphs.

## 5. Rollback Plan
- Database: Keep last known-good migration checkpoint; `alembic downgrade`.
- Backend: Re-deploy previous Docker tag / commit.
- Frontend: Re-deploy previous build artifact.
