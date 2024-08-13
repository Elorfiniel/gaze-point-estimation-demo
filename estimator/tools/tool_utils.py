import argparse
import ast
import logging

__all__ = [
  'active_root_logger',
  'parse_key_value',
  'update_kwargs_by_pop',
]


def active_root_logger():
  '''Configure root logger for command line tools.'''

  stream_handler = logging.StreamHandler()
  stream_handler.setLevel(logging.INFO)

  formatter = logging.Formatter(
    '[ %(asctime)s ] process %(process)d - %(levelname)s: %(message)s',
    datefmt='%m-%d %H:%M:%S',
  )
  stream_handler.setFormatter(formatter)

  root_logger = logging.getLogger('')
  for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
  root_logger.addHandler(stream_handler)
  root_logger.setLevel(logging.INFO)

def update_kwargs_by_pop(kwargs, update_kwargs):
  '''Update `kwargs` by poping the keys in `update_kwargs`. It's assumed that
  `kwargs` specifies all the needed key-value pairs (as defaults) so that
  `update_kwargs` can be shared across different functions.'''

  for key in kwargs.keys():
    if key in update_kwargs:
      kwargs[key] = update_kwargs.pop(key)

def parse_key_value(kv_string: str):
  try:  # split the key-value pair, where key is a string, and value is a literal expression
    key, value = kv_string.split(sep='=', maxsplit=1)
    key, value = key.strip(), value.strip()
    return key, ast.literal_eval(value)
  except Exception as e:
    raise argparse.ArgumentTypeError(f"invalid argument '{kv_string}', expecting 'key=value', "
                                     "where key is a string, and value is a literal expression"
                                     "such as strings, numbers, tuples, lists, dicts, ...")
