import winreg


class _Registry:
    def __init__(self):
        self.hkey_user = winreg.HKEY_CURRENT_USER
    
    def getvalue(self, key: str, value: str) -> str:
        try:
            key = winreg.OpenKey(self.hkey_user, key)
        except:
            return ""
        else:
            return winreg.QueryValueEx(key, value)[0]
    
    def is_dark_mode(self) -> bool:
        res = self.getvalue(
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            "AppsUseLightTheme")
        if not isinstance(res, int):
            return False
        return res == 0
    
    def colorization_color(self) -> str:
        res = self.getvalue(r"Software\Microsoft\Windows\DWM", "ColorizationColor")
        if not isinstance(res, int):
            return "#0090ee"
        value = res & 0xFFFFFF
        return f"#{value:06x}"
system = _Registry()
