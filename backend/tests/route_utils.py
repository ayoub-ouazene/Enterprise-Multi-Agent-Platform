"""Helper to flatten FastAPI routes including _IncludedRouter wrappers."""
from fastapi.routing import APIRoute


def flatten_routes(app):
    routes = []
    for route in app.routes:
        if type(route).__name__ == "_IncludedRouter":
            prefix = getattr(route.include_context, "prefix", "")
            for inner in route.original_router.routes:
                if isinstance(inner, APIRoute):
                    # Append prefix if inner path doesn't already have it
                    if prefix and not inner.path.startswith(prefix):
                        inner.path = prefix + inner.path
                    routes.append(inner)
        elif isinstance(route, APIRoute):
            routes.append(route)
    return routes
