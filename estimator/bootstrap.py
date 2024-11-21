# Enable multiprocessing for the bundled app, as described in the following links:
#   1. https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#multi-processing
#   2. https://stackoverflow.com/questions/24944558/pyinstaller-built-windows-exe-fails-with-multiprocessing
if __name__ == '__main__':
  from multiprocessing import freeze_support
  freeze_support()  # Fix issues on Windows


from estimator import (
  configure_logging, deep_update, load_toml_secure,
  server_hello, handle_message, broadcast_gaze, websocket_server,
)
from runtime.bundle import is_running_in_bundle, get_bundled_path

import argparse
import asyncio
import contextlib
import functools
import http.server as hs
import logging
import os.path as osp
import socket
import sys
import threading
import websockets


_ALLOWED_KEYS_FOR_CONFIG = [
  'camera_id', 'topleft_offset', 'screen_size_px', 'screen_size_cm',
  'game_settings',
]


def create_httpd(host, port, directory):
  class QuietHandler(hs.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
      pass  # Disable logging from the server

  handler_class = functools.partial(QuietHandler, directory=directory)
  handler_class.protocol_version = 'HTTP/1.0'

  infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, flags=socket.AI_PASSIVE)
  family, _, _, _, sockaddr = next(iter(infos))

  class DualStackServer(hs.ThreadingHTTPServer):
    '''Simple http server that binds to both IPv4 and IPv6 addresses.'''

    address_family = family

    def server_bind(self):
      '''Implementation copied from `http.server`.'''
      with contextlib.suppress(Exception):
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
      return super().server_bind()

  return DualStackServer(sockaddr, handler_class)


async def server_process(websocket, stop_future, device_config):
  logging.info('websocket server started, listening for requests')

  record_path = device_config.pop('record_path', '')
  if record_path:
    logging.info(f'recording mode on, save recordings to {record_path}')
    record_path = osp.abspath(record_path)

  # Load configuration for the PoG estimator
  config_path = get_bundled_path(osp.join('_app_data', 'estimator.toml'))
  config = load_toml_secure(config_path)
  config['__config_path'] = config_path

  new_config = device_config.copy()
  for key in device_config.keys():
    if not key in _ALLOWED_KEYS_FOR_CONFIG:
      new_config.pop(key)
  config = deep_update(config, new_config)

  # Send "server-on" to notify the client
  await server_hello(websocket, config, record_path != '', config.pop('game_settings'))

  camera_status = {}
  server_alive = True

  while server_alive:
    try:  # Wait for the message until a timeout occurs
      message = await asyncio.wait_for(websocket.recv(), timeout=0.01)
    except websockets.ConnectionClosed:
      break # Close server upon closed client
    except asyncio.TimeoutError:
      message = None

    if message is not None:
      should_exit = await handle_message(
        message, websocket, camera_status,
        config=config,
        record_path=record_path,
        stop_future=stop_future,
      )
      server_alive = not should_exit

    if camera_status.get('camera-proc', None):
      await broadcast_gaze(websocket, camera_status)

  logging.info('websocket server closed, waiting for next new request')



def websocket_server_thread(host, port, device_config, httpd):
  '''Websocket server thread, runs the camera process on the backend.'''

  logging.info('starting the websocket server to listen for client requests')

  ws_handler = functools.partial(server_process, device_config=device_config)
  try:  # Run websocket server until gracefully terminated
    asyncio.run(websocket_server(ws_handler, host, port))
  except KeyboardInterrupt:
    pass  # Ignore traceback if no websocket handler is running

  logging.info('shutting down http server')
  httpd.shutdown()

  logging.info('websocket finished execution, now exiting')


def http_server_thread(httpd, http_host, http_port):
  '''Http server thread, runs the preconfigured http server.'''

  logging.info('starting the http server to serve static content')

  with httpd:
    try:  # Serve incoming requests
      logging.info(f'game hosted on http://{http_host}:{http_port}/demo.html')
      httpd.serve_forever()
    except KeyboardInterrupt:
      pass  # Exit on received Ctrl-C
    finally:
      httpd.server_close()

  logging.info('http server finished execution, now exiting')



def main_procedure(cmdargs: argparse.Namespace):
  if not is_running_in_bundle():
    logging.error('this script should only be run from the bundled app.')
    sys.exit(1) # Exit the execution

  device_config_path = osp.abspath(cmdargs.config)
  device_config = load_toml_secure(device_config_path)
  if device_config is None:
    logging.error(f'please provide a valid configuration file with "--config <config>"')
    sys.exit(1) # Exit the execution

  httpd = create_httpd(
    cmdargs.http_host, cmdargs.http_port, get_bundled_path(osp.join('_app_data', 'sketch')),
  )

  http_thread = threading.Thread(
    target=http_server_thread,
    args=(httpd, cmdargs.http_host, cmdargs.http_port),
  )
  http_thread.start()

  websocket_server_thread(cmdargs.host, cmdargs.port, device_config, httpd)
  http_thread.join()



if __name__ == '__main__':
  configure_logging(logging.INFO, force=True)

  parser = argparse.ArgumentParser(description='Bootstrap the server and the client for bundled app.')

  parser.add_argument('--config', type=str, default='config.toml',
                      help='Device-specific configuration for this PoG estimator.')

  # These options are for the websocket server. Users should not need to change these.
  parser.add_argument('--host', type=str, default='localhost',
                      help='The host address to bind the server to. Default is localhost.')
  parser.add_argument('--port', type=int, default=4200,
                      help='The port number to bind the server to. Default is 4200.')

  # These options are for the HTTP server. They determine the URL to open in the browser.
  parser.add_argument('--http-host', type=str, default='localhost',
                      help='The host address to bind the HTTP server to. Default is localhost.')
  parser.add_argument('--http-port', type=int, default=5500,
                      help='The port number to bind the HTTP server to. Default is 5500.')

  main_procedure(parser.parse_args())
