# Enable multiprocessing for the bundled app, as described in the following links:
#   1. https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#multi-processing
#   2. https://stackoverflow.com/questions/24944558/pyinstaller-built-windows-exe-fails-with-multiprocessing
if __name__ == '__main__':
  from multiprocessing import freeze_support
  freeze_support()  # Fix issues on Windows


from runtime.bundle import is_running_in_bundle, get_bundled_path
from runtime.es_config import EsConfig, EsConfigFns
from runtime.server import http_server

from estimator import (
  configure_logging, websocket_handler,
  run_http_server, run_websocket_server,
)

import argparse
import functools
import logging
import os.path as osp
import sys
import threading


def entry_server_mode(config_updater_path):
  '''Serve the eye shooting game, until interrupted or stopped.'''

  content_root = get_bundled_path(osp.join('_app_data', 'sketch'))

  config_path = get_bundled_path(osp.join('_app_data', 'estimator.toml'))
  config_updater = EsConfig.from_toml(config_updater_path).to_dict()
  es_config = EsConfig.from_toml(config_path, config_updater)
  EsConfigFns.set_config_path(es_config, config_path)

  http_server_addr = EsConfigFns.http_server_addr(es_config)
  ws_server_addr = EsConfigFns.ws_server_addr(es_config)

  httpd = http_server(directory=content_root, **http_server_addr)
  http_thread = threading.Thread(target=run_http_server, args=(httpd, ))
  http_thread.start()

  game_url = 'http://{host}:{port}/demo.html'.format(**http_server_addr)
  logging.info(f'serving eye shooting game on {game_url}')

  ws_handler = functools.partial(websocket_handler, es_config=es_config)
  run_websocket_server(ws_handler, httpd, **ws_server_addr)

  http_thread.join()



def main_procedure(cmdargs: argparse.Namespace):
  if not is_running_in_bundle():
    logging.error('this script should only be run from the bundled app')
    sys.exit(1) # Exit the execution

  config_updater_path = osp.abspath(cmdargs.config)
  entry_server_mode(config_updater_path)



if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Bootstrap the server and the client for bundled app.')

  parser.add_argument('--config', type=str, default='config.toml',
                      help='Device-specific configuration for this PoG estimator.')

  configure_logging(logging.INFO, force=True)
  main_procedure(parser.parse_args())
