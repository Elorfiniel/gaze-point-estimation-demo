# A convinient helper class to manage log runtime messages

# From: https://gitee.com/elorfiniel/open-implementations-for-gaze-estimation/blob/master/opengaze/runtime/log.py
# Commit: f0c23aaee91786055fa4c776d05044577e30bad4
# Author: Elorfiniel (markgenthusiastic@gmail.com)

import logging
import logging.config
import os.path as osp


__all__ = ['runtime_logger']


LOGGING_CONFIG = {
  'version': 1,
  'disable_existing_loggers': False,
  'formatters': {
    'simple': {
      'format': '[ %(asctime)s ] [ %(name)s ] process %(process)d - %(levelname)s: %(message)s',
      'datefmt': '%Y-%m-%dT%H:%M:%S',
    },
  },
  'handlers': {
    'console': {
      'class': 'logging.StreamHandler',
      'level': 'INFO',
      'formatter': 'simple',
    },
  },
  'loggers': {},  # Runtime loggers
}

FILE_HANDLER_CONFIG = {
  'class': 'logging.FileHandler',
  'level': 'INFO',
  'formatter': 'simple',
  'filename': 'main.log',
}


def runtime_logger(name: str, level: int = logging.INFO, log_file: str = ''):
  '''Create a runtime logger with given name and level.'''

  if not name in LOGGING_CONFIG['loggers']:
    if log_file:
      handler_config = FILE_HANDLER_CONFIG.copy()
      handler_config['filename'] = osp.abspath(log_file)
      LOGGING_CONFIG['handlers'][name] = handler_config

    handlers = ['console', name] if log_file else ['console']

    logger_config = dict(level=level, handlers=handlers, propagate=False)
    LOGGING_CONFIG['loggers'][name] = logger_config

    logging.config.dictConfig(LOGGING_CONFIG)

  return logging.getLogger(name)
