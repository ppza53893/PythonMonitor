import sys
import importlib
from typing import Optional, List, Union

import clr


__all__ = ["import_module"]


def import_module(
    assembly: str,
    module_name: Optional[str] = None,
    submodule_or_classes: Optional[Union[List, str]] = None) -> Union[object, List[object]]:
    """
    Import a module from the CLR and return the module object(s).
    
    Args:
        assembly: The assembly name.
        module_name: The module name. If None, the assembly name is used.
        submodule_or_classes: A list of name to import from the module.
    
    Returns:
        The module object(s).
    """
    # if already imported, return the module object
    if assembly in sys.modules:
        return sys.modules[assembly]
    if clr.FindAssembly(assembly) is None:
        raise ImportError(f"{assembly} not found in CLR")

    clr.AddReference(assembly)
    
    module_name = module_name or assembly
    module_sep = module_name.split(".")
    if module_sep[0] != 'System':
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            # https://github.com/pythonnet/pythonnet/issues/678
            module = __import__(module_name)
    else:
        module = clr.System
        for m in module_sep[1:]:
            module = getattr(module, m)
    
    if submodule_or_classes is not None:
        # get the classes or modules from the module
        if isinstance(submodule_or_classes, str):
            return getattr(module, submodule_or_classes)
        else:
            return [getattr(module, m) for m in submodule_or_classes]
    else:
        return module


def test_module_import_error(
    assembly: str,
    module_name: Optional[str] = None,
    submodule_or_classes: Optional[Union[List, str]] = None):
    try:
        modules = import_module(assembly, module_name, submodule_or_classes)
    except (ImportError, ModuleNotFoundError) as e:
        print(e)
    else:
        if not isinstance(modules, list):
            modules = [modules]
        print(*modules, sep="\n")
        print('passed.')


def test_import_module():
    test_module_import_error("System.Windows.Forms")
    test_module_import_error("System.Management")
    test_module_import_error("System.Diagnostics.Process", "System.Diagnostics")
    test_module_import_error("System.Drawing", None, ["Icon", "SystemIcons"])
    test_module_import_error("OpenHardwareMonitorLib", "OpenHardwareMonitor", 'Hardware')


if __name__ == "__main__":
    test_import_module()
    