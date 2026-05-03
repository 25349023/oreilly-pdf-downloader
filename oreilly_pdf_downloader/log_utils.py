import inspect
import logging
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar, cast


@contextmanager
def log_step(logger: logging.Logger, message: str, level: int) -> Any:
    logger.log(level, f'Start: {message}')
    try:
        yield
    except Exception as e:
        logger.error(f'Error during {message}: {e}')
        raise
    logger.log(level, f'Finish: {message}')


P = ParamSpec('P')
R = TypeVar('R')


def with_log(logger: logging.Logger, message: str, level: int) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        sig = inspect.signature(func)
        is_async = inspect.iscoroutinefunction(func)

        def get_message(*args: P.args, **kwargs: P.kwargs) -> str:
            if '{' not in message:
                return message

            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            return message.format(**bound_args.arguments)

        if is_async:

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                with log_step(logger, get_message(*args, **kwargs), level=level):
                    return await func(*args, **kwargs)  # type: ignore

            return cast(Callable[P, R], async_wrapper)
        else:

            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                with log_step(logger, get_message(*args, **kwargs), level=level):
                    return func(*args, **kwargs)

            return wrapper

    return decorator
