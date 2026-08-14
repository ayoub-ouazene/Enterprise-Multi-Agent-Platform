"""Non-interactive runner for the demo seed (dev environment only)."""
import asyncio

from .seed_demo import seed


asyncio.run(seed("Demo12345678!"))
