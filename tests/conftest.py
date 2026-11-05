import pytest
from fastapi.testclient import TestClient

from fde_secure_rag.app import create_app
from fde_secure_rag.fixtures import seed_service
from fde_secure_rag.service import RagService
from fde_secure_rag.store import Store


@pytest.fixture()
def service():
    return seed_service(Store())  # fresh in-memory DB per test


@pytest.fixture()
def empty_service():
    return RagService(Store())


@pytest.fixture()
def client(service):
    return TestClient(create_app(service))


def headers(identity):
    return {
        "X-Tenant-Id": identity.tenant_id,
        "X-User-Id": identity.user_id,
        "X-Groups": ",".join(identity.groups),
    }
