from copy import deepcopy
from typing import List, Optional, Set, Tuple, Union

from packaging.markers import Variable
from packaging.requirements import Requirement


def dependencies_with_extras(deps: List[Requirement], extras: Set[str]) -> List[Requirement]:
    result: List[Requirement] = []
    for req in deps:
        req = deepcopy(req)
        markers: List[Union[str, Tuple[Variable, Variable, Variable]]] = getattr(req.marker, "_markers", []) or []
        # find the extra marker (if has)
        _at: Optional[int] = None
        extra: Optional[str] = None
        for _at, (marker_key, op, marker_value) in (
            (_at_marker, marker)
            for _at_marker, marker in enumerate(markers)
            if isinstance(marker, tuple) and len(marker) == 3
        ):
            if marker_key.value == "extra" and op.value == "==":  # pragma: no branch
                extra = marker_value.value
                del markers[_at]
                _at -= 1
                if _at > 0 and (isinstance(markers[_at], str) and markers[_at] in ("and", "or")):
                    del markers[_at]
                if len(markers) == 0:
                    req.marker = None
                break
        if not (extra is None or extra in extras):
            continue
        result.append(req)
    return result
