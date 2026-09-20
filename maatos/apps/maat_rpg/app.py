from shared.core.plugin_loader import PluginManager

PLUGIN_SHARED = os.path.join(ROOT, "shared/plugins")
PLUGIN_LOCAL  = os.path.join(APP_ROOT, "plugins")

plugins = PluginManager(
    shared_root=PLUGIN_SHARED,
    app_root=PLUGIN_LOCAL
)

plugins.load_all()