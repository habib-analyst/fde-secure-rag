"""Run the API with the seeded synthetic corpus: python -m fde_secure_rag.serve"""
from __future__ import annotations

import uvicorn

from .app import create_app
from .fixtures import seed_service


def main():
    service = seed_service()
    uvicorn.run(create_app(service), host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
