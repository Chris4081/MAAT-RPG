"""Local chat archive, separate from retrieval memory and game progress."""
from contextlib import closing, contextmanager
from datetime import datetime
import os
from pathlib import Path
import sqlite3

UNLOCK_MESSAGES = 5
PAGE_SIZE = 100


class ChatHistory:
    def __init__(self, profile_root):
        self.root = Path(profile_root)
        self.path = self.root / 'data' / 'chat_history.db'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch(mode=0o600, exist_ok=True)
        if os.name == 'posix':
            self.path.chmod(0o600)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL, epoch REAL NOT NULL, day TEXT NOT NULL,
                    role TEXT NOT NULL, content TEXT NOT NULL, mode TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS chat_day ON messages(day, epoch, id);
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
            ''')
            if not db.execute("SELECT 1 FROM metadata WHERE key='secure_storage_v1'").fetchone():
                # Older releases used ordinary DELETE. Remove their free-page
                # remnants once, including entries deleted before this upgrade.
                # No VACUUM INTO/backup copy containing old messages is retained.
                db.execute('VACUUM')
                db.execute("INSERT OR IGNORE INTO metadata(key,value) VALUES ('secure_storage_v1','1')")

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.path, timeout=2)) as db:
            db.row_factory = sqlite3.Row
            # These settings are connection-local: apply to worker AND UI.
            # ON, not FAST, also scrubs released overflow/freelist pages.
            if db.execute('PRAGMA secure_delete=ON').fetchone()[0] != 1:
                raise sqlite3.OperationalError('Sicheres Überschreiben ist nicht verfügbar.')
            db.execute('PRAGMA synchronous=EXTRA')
            db.execute('PRAGMA fullfsync=ON')
            db.execute('PRAGMA checkpoint_fullfsync=ON')
            db.execute('PRAGMA temp_store=MEMORY')
            db.execute('PRAGMA journal_size_limit=0')
            if db.execute('PRAGMA journal_mode').fetchone()[0] == 'wal':
                # A previous/external connection may have enabled WAL. Let
                # SQLite checkpoint it; never unlink or overwrite a live WAL.
                if db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0]:
                    raise sqlite3.OperationalError('Das Archiv wird gerade verwendet. Bitte erneut versuchen.')
            mode = db.execute('PRAGMA journal_mode=TRUNCATE').fetchone()[0]
            if mode != 'truncate':
                raise sqlite3.OperationalError('Das Archiv-Journal konnte nicht bereinigt werden.')
            with db:
                yield db

    def claim_unlock_notice(self):
        """Claim only when the GUI can actually present the notice in chat."""
        with self.connect() as db:
            return bool(db.execute(
                "INSERT OR IGNORE INTO metadata(key,value) VALUES ('history_unlock_notice','1')").rowcount)

    @staticmethod
    def _values(role, content, mode, timestamp=None):
        if role not in ('user', 'assistant') or not isinstance(content, str) or not content.strip():
            return None
        if role == 'user' and content.lstrip().startswith('/'):
            return None
        when = datetime.fromisoformat(timestamp) if timestamp else datetime.now().astimezone()
        return (when.isoformat(), when.timestamp(), when.date().isoformat(), role, content, mode)

    def append(self, role, content, mode='adventure', timestamp=None):
        values = self._values(role, content, mode, timestamp)
        if values is None:
            return None
        with self.connect() as db:
            return db.execute('INSERT INTO messages(timestamp,epoch,day,role,content,mode) VALUES (?,?,?,?,?,?)', values).lastrowid

    def import_legacy(self):
        """One-time copy of dated messages; never edit the memory DB/vector index.

        V5 is authoritative if present; using both would duplicate conversations.
        The marker also prevents deleted archive entries from returning on restart.
        """
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM metadata WHERE key='legacy_imported'").fetchone():
                return
            source = next((self.root / 'data' / name for name in ('memory_v5.db', 'mem6.db')
                           if (self.root / 'data' / name).is_file()), None)
            if source:
                with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True, timeout=2)) as old:
                    for role, content, timestamp in old.execute('SELECT role,content,timestamp FROM episodic ORDER BY id'):
                        try:
                            values = self._values(role, content, 'legacy', timestamp)
                            if not timestamp:
                                continue  # Never invent dates for older entries.
                        except (ValueError, TypeError, OverflowError, OSError):
                            continue
                        if values:
                            db.execute('INSERT INTO messages(timestamp,epoch,day,role,content,mode) VALUES (?,?,?,?,?,?)', values)
            db.execute("INSERT INTO metadata(key,value) VALUES ('legacy_imported','1')")

    def years(self):
        with self.connect() as db:
            return [r[0] for r in db.execute('SELECT DISTINCT substr(day,1,4) FROM messages ORDER BY 1 DESC')]

    def last_activity(self):
        """Only a timestamp; deleted messages must not survive in a second cache."""
        with self.connect() as db:
            row = db.execute('SELECT timestamp FROM messages ORDER BY id DESC LIMIT 1').fetchone()
            return row[0] if row else None

    def days(self, year=None, month=None, newest=True):
        clauses, args = [], []
        if year:
            clauses.append('substr(day,1,4)=?'); args.append(str(int(year)))
        if month:
            clauses.append('substr(day,6,2)=?'); args.append(f'{int(month):02d}')
        where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
        order = 'DESC' if newest else 'ASC'
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                'SELECT day,COUNT(*) AS count,MAX(id) AS last_id FROM messages' + where +
                ' GROUP BY day ORDER BY day ' + order, args)]

    def messages(self, day, page=0):
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                'SELECT * FROM messages WHERE day=? ORDER BY epoch,id LIMIT ? OFFSET ?',
                (day, PAGE_SIZE, max(0, int(page)) * PAGE_SIZE))]

    def get(self, identifier):
        with self.connect() as db:
            row = db.execute('SELECT * FROM messages WHERE id=?', (int(identifier),)).fetchone()
            return dict(row) if row else None

    def delete_message(self, identifier):
        with self.connect() as db:
            return db.execute('DELETE FROM messages WHERE id=?', (int(identifier),)).rowcount

    def delete_day(self, day, through_id):
        # Messages arriving while the confirmation is open were not reviewed.
        with self.connect() as db:
            return db.execute('DELETE FROM messages WHERE day=? AND id<=?', (day, int(through_id))).rowcount
