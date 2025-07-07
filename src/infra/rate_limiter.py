"""
API Rate Limiter and Retry Decorator Stub
"""

import time
import functools


def rate_limited(max_per_second):
    min_interval = 1.0 / float(max_per_second)

    def decorator(func):
        last_time = [0.0]

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_time[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            last_time[0] = time.time()
            return func(*args, **kwargs)

        return wrapper

    return decorator
