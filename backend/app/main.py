from fastapi import FastAPI


app = FastAPI(title="Enterprise Multi-Agent Platform API")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
