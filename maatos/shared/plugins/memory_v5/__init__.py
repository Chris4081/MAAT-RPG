    def __init__(self):
        base = os.path.join(os.path.dirname(__file__), "..", "..", "data")
        self.base_path = os.path.abspath(base)

        self.db_path = os.path.join(self.base_path, "memory_v5.db")
        self.index_path = os.path.join(self.base_path, "semantic.index")
        self.identity_path = os.path.join(self.base_path, "maat_identity.json")

        self._init_db()
        self._init_identity()
        self._init_vector_index()

        # 🔥 Debug-Flags initialisieren
        self.debug = False
        self.debug_once = False