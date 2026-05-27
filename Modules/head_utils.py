import types
from importlib.machinery import SourceFileLoader

from Modules.common import HEAD_MODULE_PATH

_head_module = None


def get_head_module():
    global _head_module
    if _head_module is not None:
        return _head_module

    loader = SourceFileLoader("leaf_head_module", HEAD_MODULE_PATH)
    module = types.ModuleType(loader.name)
    loader.exec_module(module)
    _head_module = module
    return _head_module
