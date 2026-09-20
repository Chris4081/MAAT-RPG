"""Per-instance native model defaults for the Intel adapter.

The tested llama-cpp-python 0.3.34 does not expose use_extra_bufts in Llama's
constructor. Rebind ONLY that constructor's API reference to a forwarding
proxy, so its native model defaults can disable weight repacking. The
installed module, ARM adapter, native function and C structure layout remain
unchanged. No global monkey-patch, copied dependency or on-disk patch is used.
"""
from types import FunctionType
from llama_cpp import Llama


class _ModelDefaults:
    def __init__(self, api, repack):
        self.api, self.repack = api, repack

    def __getattr__(self, name):
        return getattr(self.api, name)

    def llama_model_default_params(self):
        params = self.api.llama_model_default_params()
        # Older releases without this native option retain their own defaults.
        if hasattr(params, 'use_extra_bufts'):
            params.use_extra_bufts = self.repack
        return params


class IntelLlama(Llama):
    def __init__(self, *args, repack_weights=False, **kwargs):
        original = Llama.__init__
        if not isinstance(original, FunctionType) or 'llama_cpp' not in original.__globals__:
            raise RuntimeError('GGUF (Intel): incompatible llama-cpp-python constructor')
        scope = dict(original.__globals__)
        scope['llama_cpp'] = _ModelDefaults(scope['llama_cpp'], bool(repack_weights))
        initialize = FunctionType(original.__code__, scope, original.__name__,
                                  original.__defaults__, original.__closure__)
        initialize.__kwdefaults__ = original.__kwdefaults__
        initialize(self, *args, **kwargs)
        self.intel_repacking = getattr(self.model_params, 'use_extra_bufts', None)
