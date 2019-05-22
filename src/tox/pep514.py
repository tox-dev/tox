"""Implement https://www.python.org/dev/peps/pep-0514/ to discover interpreters"""
import os

import winreg

from tox.interpreters import PythonSpec


def enum_keys(key):
    at = 0
    while True:
        try:
            yield winreg.EnumKey(key, at)
        except OSError:
            break
        at += 1


def get_value(key, value_name):
    try:
        return winreg.QueryValue(key, value_name)
    except FileNotFoundError:
        return None


def discover_pythons():
    for hive, key, flags, arch in [
        (winreg.HKEY_CURRENT_USER, r"Software\Python", 0, None),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Python", winreg.KEY_WOW64_64KEY, 64),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Python", winreg.KEY_WOW64_32KEY, 32),
    ]:
        for spec in open_set(arch, flags, hive, key):
            yield spec


def open_set(arch, flags, hive, key):
    try:
        with winreg.OpenKeyEx(hive, key, access=winreg.KEY_READ | flags) as root_key:
            for company in enum_keys(root_key):
                if company == "PyLauncher":  # reserved
                    continue
                for spec in open_company(arch, company, root_key):
                    yield spec
    except FileNotFoundError:
        pass


def open_company(arch, company, root_key):
    with winreg.OpenKey(root_key, company) as company_key:
        for tag in enum_keys(company_key):
            for spec in open_tag(arch, company, company_key, tag):
                yield spec


def open_tag(arch, company, company_key, tag):
    with winreg.OpenKey(company_key, tag) as tag_key:
        version_str = get_value(tag_key, "SysVersion") or tag[:3]
        major, minor = list(int(i) for i in version_str.split("."))
        arch_str = get_value(tag_key, "SysArchitecture") or None
        arch = arch if arch_str is None else arch_str[: -len("bit")]
    try:
        with winreg.OpenKey(company_key, r"{}\InstallPath".format(tag)) as ip_key:
            with ip_key:
                ip = get_value(ip_key, None)
                exe = get_value(ip_key, "ExecutablePath") or os.path.join(ip, "python.exe")
                if os.path.exists(exe):
                    args = get_value(ip_key, "ExecutableArguments")
                    name = "python" if company == "PythonCore" else company
                    yield PythonSpec(name, major, minor, arch, exe, args)
    except OSError:
        pass


if __name__ == "__main__":
    print(list(discover_pythons()))
