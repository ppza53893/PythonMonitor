from .pythonnet import import_module

__all__ = [
    'dispose',
    'System',
    'system',
    'Diagnostics',
    'diagnostics',
    'Management',
    'management',
    'Forms',
    'forms',
    'container',
    'Container',
    'Icon',
    'SystemIcons',
    'NetworkInterface',
    'close_container',]


System = import_module("System")
Diagnostics = import_module("System.Diagnostics.Process", "System.Diagnostics")
Management = import_module("System.Management")
Forms = import_module("System.Windows.Forms")
Container = import_module("System.ComponentModel.Primitives", "System.ComponentModel", 'Container')
Icon, SystemIcons = import_module("System.Drawing", submodule_or_classes=["Icon", "SystemIcons"])
NetworkInterface = import_module("System.Net.NetworkInformation", submodule_or_classes=["NetworkInterface"])


system = System
diagnostics = Diagnostics
management = Management
forms = Forms
container = Container()


def dispose(*disposeobjects):
    for obj in disposeobjects:
        if hasattr(obj, 'Dispose'):
            obj.Dispose()


def close_container():
    try:
        dispose(container)
    except:
        pass
