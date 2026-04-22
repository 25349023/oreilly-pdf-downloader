import inspect
from contextlib import asynccontextmanager, contextmanager
from functools import wraps


@contextmanager
def log_step(logger, message, level):
    logger.log(level, f'Start: {message}')
    try:
        yield
    except Exception as e:
        logger.error(f'Error during {message}: {e}')
        raise
    logger.log(level, f'Finish: {message}')


def with_log(logger, message, level):
    def decorator(func):
        sig = inspect.signature(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            formatted_msg = message.format(**bound_args.arguments)

            logger.log(level, f'Start: {formatted_msg}')
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                logger.error(f'Error during {formatted_msg}: {e}')
                raise
            logger.log(level, f'Finish: {formatted_msg}')

            return result

        return wrapper

    return decorator


@asynccontextmanager
def wrap_sync(context_mgr):
    with context_mgr as resource:
        yield resource
