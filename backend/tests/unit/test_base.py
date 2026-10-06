import pytest
from sqlalchemy import CheckConstraint, Column, Integer, MetaData, String, Table, UniqueConstraint
from sqlalchemy.schema import CreateTable

from app.infrastructure.db.base import NAMING_CONVENTION, Base


def _table(metadata: MetaData, name: str) -> Table:
    return Table(
        name,
        metadata,
        Column("id", Integer, primary_key=True),
        Column("codigo", String(10)),
        Column("valor", Integer),
        UniqueConstraint("codigo"),
        CheckConstraint("valor > 0", name="valor_positivo"),
    )


@pytest.mark.parametrize("table_name", ["cosa", "otra_cosa"])
def test_base_metadata_names_constraints_deterministically(table_name: str) -> None:
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)

    ddl = str(CreateTable(_table(metadata, table_name)))

    assert f"CONSTRAINT pk_{table_name} PRIMARY KEY (id)" in ddl
    assert f"CONSTRAINT uq_{table_name}_codigo UNIQUE (codigo)" in ddl
    assert f"CONSTRAINT ck_{table_name}_valor_positivo CHECK (valor > 0)" in ddl


def test_naming_convention_covers_all_constraint_kinds() -> None:
    assert set(NAMING_CONVENTION) == {"ix", "uq", "ck", "fk", "pk"}
