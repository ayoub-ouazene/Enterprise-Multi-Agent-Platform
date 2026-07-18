from pydantic import SecretStr
from sqlalchemy.engine import URL, make_url


def normalize_asyncpg_url(value: SecretStr | str) -> URL:
    """Normalize Neon SSL query parameters without weakening SSL requirements."""
    raw_value = value.get_secret_value() if isinstance(value, SecretStr) else value
    url = make_url(raw_value)
    query = dict(url.query)

    ssl_mode = query.pop("sslmode", None)
    if ssl_mode is not None:
        existing_ssl = query.get("ssl")
        if existing_ssl is not None and existing_ssl != ssl_mode:
            raise ValueError("Conflicting SSL parameters in database URL")
        query["ssl"] = ssl_mode
        url = url.set(query=query)

    return url
