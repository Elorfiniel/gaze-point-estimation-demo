import concurrent.futures as futures
import logging


def _secure_done_fn(done_fn):
  def wrapper(future: futures.Future):
    try:
      done_fn(future) # Anticipating potential exceptions
    except Exception as ex:
      logging.error(f'task generates an exception: {ex}')

  return wrapper

def _parse_fn_and_args(task):
  if not isinstance(task, tuple): task = (task, )
  task = task + (4 - len(task)) * (None, )
  task_fn, args, kwargs, done_fn = task

  args = args if args is not None else tuple()
  kwargs = kwargs if kwargs is not None else dict()

  if done_fn is None:
    done_fn = lambda f: f.result()
  done_fn = _secure_done_fn(done_fn)

  return task_fn, args, kwargs, done_fn

def run_parallel(executor: futures.ProcessPoolExecutor, tasks):
  '''Run tasks in parallel. Each task is either a callable task_fn or
  a tuple of (task_fn, args, kwargs, done_fn). Note that args, kwargs
  and done_fn are all optional parameters.

  Args:
    `executor`: process pool executor used for parallel tasks
    `tasks`: a generator of tasks, each task can either be a callable or a tuple of
    (task_fn, args, kwargs, done_fn), where args, kwargs and done_fn are optional
  '''

  with executor:
    for task in tasks:
      task_fn, args, kwargs, done_fn = _parse_fn_and_args(task)
      future = executor.submit(task_fn, *args, **kwargs)
      future.add_done_callback(done_fn)
