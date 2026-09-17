# Known Limitations

## Database Sessions in Async Functions
Currently, the application uses a synchronous SQLAlchemy `SessionLocal()` inside `async def` functions like `retrieval.py` and `ai_logger.py`. This blocks the event loop and defeats the purpose of `async def` when DB calls are executing. At the current scale, this is acceptable, but it should be refactored to use `AsyncSession` (via `ext.asyncio` in SQLAlchemy) as the system scales to handle higher concurrency.
