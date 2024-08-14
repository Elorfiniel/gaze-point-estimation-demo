import argparse
import ast
import logging

__all__ = [
  'QuickRegistry',
  'active_root_logger',
  'update_kwargs_by_pop',
  'parse_key_value',
  'parse_file_ext',
]


class QuickRegistry():
  def __init__(self):
    '''Quick registry for storing objects on the fly.'''

    self._REGISTRY = {}

  def register(self, obj = None, *, name: str = '', force: bool = False):
    '''Register an object to the registry.

    ```
    quick_registry = QuickRegistry()

    @quick_registry.register
    def mulberry(): print('i like mulberry')

    @quick_registry.register(name='favorite')
    def banana(): print('i like banana')

    # Quick Registry
    #   'mulberry': <function mulberry at ...>
    #   'favorite': <function banana at ...>
    ```

    `obj`: the object to be registered in registry table.

    `name`: an optional name for the object, which replaces the its `__name__` property.
    Note that this argument must be passed in as a keyword argument.

    `force`: force registering when an object with the same name has been registered.
    Note that this argument must be passed in as a keyword argument.
    '''

    def register_item(_obj):
      assert hasattr(_obj, '__name__') or name, 'please provide an identifier for the object'
      name_registered = name or getattr(_obj, '__name__')

      if not name_registered in self._REGISTRY:
        self._REGISTRY[name_registered] = _obj
      else:   # warn that the name has been registered
        logging.warning(f'another object with name "{name_registered}" has been registered')
        if force:
          logging.warning(f'force registering a new object with name "{name_registered}"')
          self._REGISTRY[name_registered] = _obj

    if obj is None:
      return register_item
    else:
      register_item(obj)

  def __getitem__(self, name: str = ''):
    return self._REGISTRY.get(name, None)


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
  '''Split the key-value pair.'''

  try:  # with key a string, and value a literal expression
    key, value = kv_string.split(sep='=', maxsplit=1)
    key, value = key.strip(), value.strip()
    return key, ast.literal_eval(value)
  except Exception as e:
    raise argparse.ArgumentTypeError(f"invalid argument '{kv_string}', expecting 'key=value', "
                                     "where key is a string, and value is a literal expression"
                                     "such as strings, numbers, tuples, lists, dicts, ...")

def parse_file_ext(ext: str, leading_dot: bool = True):
  '''Parse canonical file extension string.'''

  return '.' + ext.strip('.') if leading_dot else ext.strip('.')
