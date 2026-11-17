"""Identidad de desarrollo y registro sembrado según D-18 y C-09."""

from dataclasses import dataclass
from sqlite3 import Connection

from .contracts import AccountView, ConsentRecord, utc_now


BASE_OWNER_ID = "habla-usuario-base"
BASE_CONSENT_ID = "habla-consentimiento-base-v1"


@dataclass(frozen=True)
class ActorContext:
    owner_id: str
    consent_id: str


def seed_base_user(db: Connection) -> ActorContext:
    db.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY, data TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS consents (
            id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL REFERENCES accounts(id),
            data TEXT NOT NULL
        );
    """)
    now = utc_now()
    account = AccountView(id=BASE_OWNER_ID, email="equipo@habla.invalid", created_at=now)
    consent = ConsentRecord(
        id=BASE_CONSENT_ID, owner_id=BASE_OWNER_ID, policy_version="d18-fixture-v1",
        accepted_at=now, external_processors=[],
    )
    with db:
        db.execute("INSERT OR IGNORE INTO accounts VALUES (?, ?)", (account.id, account.model_dump_json()))
        db.execute(
            "INSERT OR IGNORE INTO consents VALUES (?, ?, ?)",
            (consent.id, account.id, consent.model_dump_json()),
        )
    return ActorContext(account.id, consent.id)
