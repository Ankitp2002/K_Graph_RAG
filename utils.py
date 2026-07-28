from functools import wraps


def handle_err(func=None, *, raise_error: bool = False):
    def decorator(f):
        @wraps(f)
        def inner_wraps(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as err:
                crash_msg = (
                    f"Pipeline crashed during execution of '{f.__name__}': {err}"
                )
                if raise_error:
                    raise RuntimeError(crash_msg) from err

                print(crash_msg)
                return None

        return inner_wraps

    # Handles usage with or without parentheses
    if func is None:
        return decorator
    return decorator(func)
