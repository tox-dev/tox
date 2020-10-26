from .api import PackageType
from .artifact.dev import LegacyDevVirtualEnvPackage
from .artifact.sdist import Pep517VirtualEnvPackageSdist
from .artifact.wheel import Pep517VirtualEnvPackageWheel


def virtual_env_package_id(of_type: PackageType) -> str:
    if of_type is PackageType.sdist:
        return Pep517VirtualEnvPackageSdist.id()
    elif of_type is PackageType.wheel:
        return Pep517VirtualEnvPackageWheel.id()
    elif of_type is PackageType.dev:
        return LegacyDevVirtualEnvPackage.id()
    raise KeyError(PackageType.name)
