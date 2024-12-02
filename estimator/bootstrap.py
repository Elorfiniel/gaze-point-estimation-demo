# Enable multiprocessing for the bundled app, as described in the following links:
#   1. https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#multi-processing
#   2. https://stackoverflow.com/questions/24944558/pyinstaller-built-windows-exe-fails-with-multiprocessing
if __name__ == '__main__':
  from multiprocessing import freeze_support
  freeze_support()  # Fix issues on Windows


from runtime.bundle import is_running_in_bundle, get_bundled_path
from runtime.server import http_server

from estimator import (
  load_config, create_server_consumer,
  clean_up_context, websocket_send_json,
  send_server_hello, send_gaze_predict, recv_client_message,
  on_kill_camera, on_kill_server, on_save_result,
  run_http_server, run_websocket_server,
  configure_logging,
)

import argparse
import functools
import json
import logging
import multiprocessing as mp
import os.path as osp
import sys
import threading



async def on_open_camera(message_obj, websocket, context, config_path, record_path, device_config):
  context['camera_open'] = mp.Event()
  context['camera_kill'] = mp.Event()

  context['next_ready'] = mp.Event()
  context['next_valid'] = mp.Value('b', False)
  context['value_bank'] = mp.Array('d', (0.0, 0.0, 0.0))
  context['value_lock'] = mp.Lock()

  if record_path != '':
    context['save_queue'] = mp.Queue()
    record_info = dict(
      enable=True, cache_size=600,
      root=record_path,
      name=message_obj.get('record_name', ''),
      save_queue=context['save_queue'],
    )
  else:
    record_info = dict(enable=False)

  context['camera_proc'] = mp.Process(
    target=create_server_consumer, kwargs=dict(
      config_path=config_path,
      open_event=context['camera_open'],
      kill_event=context['camera_kill'],
      next_ready=context['next_ready'],
      next_valid=context['next_valid'],
      value_bank=context['value_bank'],
      value_lock=context['value_lock'],
      record_info=record_info,
      config_updater=device_config,
    ),
  )

  context['camera_proc'].start()
  context['camera_open'].wait()

  await websocket_send_json(websocket, { 'status': 'camera_on' })

  return False

async def websocket_handler(websocket, stop_future, device_config):
  '''Handler for incoming websocket requests, sent by main game loop.'''

  server_alive, exit_cond_1, exit_cond_2 = True, False, False

  config_path = get_bundled_path(osp.join('_app_data', 'estimator.toml'))
  config = load_config(config_path, device_config)

  record_path = config['server']['record']['path']
  await send_server_hello(websocket, config, record_path)

  handler_infos = dict(
    open_camera=dict(fn=on_open_camera, kw=dict(
      config_path=config_path,
      record_path=record_path,
      device_config=device_config,
    )),
    kill_camera=dict(fn=on_kill_camera, kw=dict()),
    kill_server=dict(fn=on_kill_server, kw=dict(stop_future=stop_future)),
    save_result=dict(fn=on_save_result, kw=dict(record_path=record_path)),
  )

  context = dict()  # Context shared by handler functions
  while server_alive:
    await send_gaze_predict(websocket, context)

    exit_cond_1, message = await recv_client_message(websocket)

    if message is not None:
      message_obj = json.loads(message) # Deserialize
      info = handler_infos[message_obj['opcode']]
      args = (message_obj, websocket, context)
      exit_cond_2 = await info['fn'](*args, **info['kw'])

    server_alive = not exit_cond_1 and not exit_cond_2

  clean_up_context(context)



def entry_server_mode(device_config_path):
  '''Serve the eye shooting game, until interrupted or stopped.'''

  content_root = get_bundled_path(osp.join('_app_data', 'sketch'))

  device_config = load_config(device_config_path)
  server_config = load_config(
    config_path=get_bundled_path(osp.join('_app_data', 'estimator.toml')),
    config_updater=device_config,
  )['server']
  httpd = http_server(directory=content_root, **server_config['http'])

  http_thread = threading.Thread(target=run_http_server, args=(httpd, ))
  http_thread.start()

  game_url = 'http://{host}:{port}/demo.html'.format(**server_config['http'])
  logging.info(f'serving eye shooting game on {game_url}')

  ws_handler = functools.partial(websocket_handler, device_config=device_config)
  run_websocket_server(ws_handler, httpd, **server_config['websocket'])

  http_thread.join()



def main_procedure(cmdargs: argparse.Namespace):
  if not is_running_in_bundle():
    logging.error('this script should only be run from the bundled app')
    sys.exit(1) # Exit the execution

  device_config_path = osp.abspath(cmdargs.config)
  entry_server_mode(device_config_path)



if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Bootstrap the server and the client for bundled app.')

  parser.add_argument('--config', type=str, default='config.toml',
                      help='Device-specific configuration for this PoG estimator.')

  configure_logging(logging.INFO, force=True)
  main_procedure(parser.parse_args())
