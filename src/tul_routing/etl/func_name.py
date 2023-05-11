from typing import Any

def func_name(mtd: Any, *args):
    extra = '' if not args else f" ({', '.join(map(str, args))})"
    try:
        func = mtd.__func__
        return f"{func.__module__}.{func.__name__}{extra}"
    except Exception:
        try:
            return f"{mtd.__name__}{extra}"
        except Exception:
            pass

    return f"{(str(mtd))}{extra}"