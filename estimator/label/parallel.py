from typing import Callable, Dict, Generator, Tuple

import concurrent.futures as futures
import logging


def secure_done_fn(done_fn: Callable):
  def wrapper(future: futures.Future):
    try:
      done_fn(future) # Anticipating potential exceptions
    except Exception as ex:
      logging.error(f'task generates an exception: {ex}')

  return wrapper


ParaTask = Tuple[Callable, Tuple, Dict, Callable]

def run_parallel(executor: futures.ProcessPoolExecutor,
                 tasks: Generator[ParaTask, None, None]):
  '''Run tasks in parallel. Each task is a tuple of (task_fn, args, kwargs, done_fn).
  If no done_fn is provided (`done_fn=None`), a default done_fn will be used.

  Args:
    `executor`: process pool executor used for parallel tasks
    `tasks`: a generator of tasks, each task is a tuple of (task_fn, args, kwargs, done_fn)
  '''

  with executor:
    for task_fn, args, kwargs, done_fn in tasks:
      future = executor.submit(task_fn, *args, **kwargs)
      if done_fn is None:
        done_fn = lambda f: f.result()
      done_fn = secure_done_fn(done_fn)
      future.add_done_callback(done_fn)
