import importlib.util
import os
import sys


SKILL_SCRIPT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../.gemini/skills/crm-lead-manager/scripts/lead_manager.py",
    )
)

_SPEC = importlib.util.spec_from_file_location("cm_lead_manager_impl", SKILL_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load lead manager implementation from {SKILL_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


__all__ = [name for name in dir(_MODULE) if not name.startswith("_")]
globals().update({name: getattr(_MODULE, name) for name in __all__})


if __name__ == "__main__":
    sys.exit(_MODULE.main())
