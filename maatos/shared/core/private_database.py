"""SQLite connections for private archives; commits remain crash-recoverable."""
import os
from pathlib import Path
import sqlite3


class PrivateConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def connect(path, timeout=2):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():path.touch(mode=0o600,exist_ok=True)
    if os.name=='posix':path.chmod(0o600)
    db=sqlite3.connect(path,timeout=timeout,factory=PrivateConnection)
    try:
        db.row_factory=sqlite3.Row
        if db.execute('PRAGMA secure_delete=ON').fetchone()[0]!=1:
            raise sqlite3.OperationalError('Sicheres Überschreiben ist nicht verfügbar.')
        db.execute('PRAGMA synchronous=EXTRA'); db.execute('PRAGMA fullfsync=ON')
        db.execute('PRAGMA checkpoint_fullfsync=ON'); db.execute('PRAGMA temp_store=MEMORY')
        db.execute('PRAGMA journal_size_limit=0')
        if db.execute('PRAGMA journal_mode').fetchone()[0]=='wal':
            if db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0]:
                raise sqlite3.OperationalError('Die Datenbank wird gerade verwendet. Bitte erneut versuchen.')
        if db.execute('PRAGMA journal_mode=TRUNCATE').fetchone()[0]!='truncate':
            raise sqlite3.OperationalError('Das Datenbank-Journal konnte nicht bereinigt werden.')
        return db
    except BaseException:
        db.close(); raise
