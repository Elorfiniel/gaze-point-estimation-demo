import logging
import os
import toml


def configure_logging(level=logging.INFO, force=False):
  logging.basicConfig(
    level=level, force=force,
    format='[ %(asctime)s ] process %(process)d - %(levelname)s: %(message)s',
    datefmt='%m-%d %H:%M:%S',
  )


def load_toml_secure(toml_path):
  '''Load toml file with caution, return None if failed.'''

  toml_data = None

  if os.path.isfile(toml_path):
    with open(toml_path, 'r') as toml_file:
      try:
        toml_data = toml.load(toml_file)
      except:
        toml_data = None

  if toml_data is None:
    logging.error(f'cannot load from TOML file "{toml_path}"')

  return toml_data
