"""
Teste de integração para cleanup_old_checkpoints().

Requer BD real configurado no .env — não usa mock.

Rodar com:
    pytest tests/test_cleanup_checkpoints.py -v
"""

import uuid
import pytest
from src.db.connection import get_vector_conn
from src.db.checkpointer import setup_checkpointer, cleanup_old_checkpoints


# ──────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────

def insert_checkpoint(cursor, thread_id: str, checkpoint_id: str):
    """Insere um checkpoint mínimo válido nas 3 tabelas."""
    cursor.execute(
        """
        INSERT INTO checkpoints (thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata)
        VALUES (%s, '', %s, NULL, 'empty', '{}'::jsonb, '{}'::jsonb)
        ON CONFLICT DO NOTHING
        """,
        (thread_id, checkpoint_id),
    )
    cursor.execute(
        """
        INSERT INTO checkpoint_blobs (thread_id, checkpoint_ns, channel, version, type, blob)
        VALUES (%s, '', 'test_channel', %s, 'empty', NULL)
        ON CONFLICT DO NOTHING
        """,
        (thread_id, checkpoint_id),
    )
    cursor.execute(
        """
        INSERT INTO checkpoint_writes (thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, type, blob, task_path)
        VALUES (%s, '', %s, %s, 0, 'test_channel', 'empty', ''::bytea, '')
        ON CONFLICT DO NOTHING
        """,
        (thread_id, checkpoint_id, str(uuid.uuid4())),
    )


def count_checkpoints(cursor, thread_id: str) -> int:
    cursor.execute(
        "SELECT COUNT(*) as total FROM checkpoints WHERE thread_id = %s",
        (thread_id,),
    )
    return cursor.fetchone()["total"]


def delete_thread(cursor, thread_id: str):
    cursor.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (thread_id,))
    cursor.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (thread_id,))
    cursor.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))


# ──────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def ensure_checkpointer_tables():
    setup_checkpointer()


@pytest.fixture()
def thread_id():
    return f"test_thread_{uuid.uuid4().hex[:8]}"


@pytest.fixture()
def conn():
    connection = get_vector_conn()
    yield connection
    connection.rollback()
    connection.close()


# ──────────────────────────────────────────
# Testes
# ──────────────────────────────────────────

def test_cleanup_removes_old_keeps_recent(thread_id, conn):
    """Insere 6 checkpoints, roda cleanup(keep=3), verifica que sobraram 3."""
    cursor = conn.cursor()

    try:
        for _ in range(6):
            insert_checkpoint(cursor, thread_id, str(uuid.uuid4()))
        conn.commit()

        assert count_checkpoints(cursor, thread_id) == 6

        cleanup_old_checkpoints(keep=3)

        assert count_checkpoints(cursor, thread_id) == 3

    finally:
        delete_thread(cursor, thread_id)
        conn.commit()
        cursor.close()


def test_cleanup_does_nothing_when_below_keep(thread_id, conn):
    """Insere 2 checkpoints com keep=3 — nenhum deve ser deletado."""
    cursor = conn.cursor()

    try:
        for _ in range(2):
            insert_checkpoint(cursor, thread_id, str(uuid.uuid4()))
        conn.commit()

        cleanup_old_checkpoints(keep=3)

        assert count_checkpoints(cursor, thread_id) == 2

    finally:
        delete_thread(cursor, thread_id)
        conn.commit()
        cursor.close()


def test_cleanup_isolated_between_threads(conn):
    """Dois threads distintos — limpeza de um não afeta o outro."""
    thread_a = f"test_thread_{uuid.uuid4().hex[:8]}"
    thread_b = f"test_thread_{uuid.uuid4().hex[:8]}"
    cursor = conn.cursor()

    try:
        for _ in range(5):
            insert_checkpoint(cursor, thread_a, str(uuid.uuid4()))

        for _ in range(2):
            insert_checkpoint(cursor, thread_b, str(uuid.uuid4()))

        conn.commit()

        cleanup_old_checkpoints(keep=3)

        assert count_checkpoints(cursor, thread_a) == 3
        assert count_checkpoints(cursor, thread_b) == 2

    finally:
        delete_thread(cursor, thread_a)
        delete_thread(cursor, thread_b)
        conn.commit()
        cursor.close()