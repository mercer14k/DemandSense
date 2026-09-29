import os
from uuid import uuid4

import pytest
from demandsense.schemas import RunRequest
from demandsense.services import ForecastService
from demandsense.storage import Repository, metadata


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to a disposable PostgreSQL database"
)
def test_postgres_persistence_across_repository_instances():
    url = os.environ["TEST_DATABASE_URL"]
    schema = "test_" + uuid4().hex
    from sqlalchemy import create_engine

    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    from sqlalchemy.schema import CreateSchema, DropSchema

    with engine.begin() as conn:
        conn.execute(CreateSchema(schema))
    repo = Repository(url)
    repo.engine.dispose()
    repo.engine = engine
    repo.read_engine = engine
    try:
        metadata.create_all(engine)
        repo.seed(2, 196)
        run = ForecastService(repo).create_run(RunRequest(sku="SKU-0001", location="CHI"))
        assert run["forecast"]
        with engine.connect() as conn:
            from demandsense.storage import runs
            from sqlalchemy import select

            assert (
                conn.execute(select(runs.c.payload).where(runs.c.id == run["id"])).scalar_one()["id"]
                == run["id"]
            )
    finally:
        with engine.begin() as conn:
            conn.execute(DropSchema(schema, cascade=True))
        engine.dispose()
