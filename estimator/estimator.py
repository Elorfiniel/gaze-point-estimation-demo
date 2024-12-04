from runtime.captures import VideoCaptureBuilder, CaptureHandler
from runtime.es_config import EsConfig, EsConfigFns
from runtime.facealign import FaceAlignment
from runtime.inference import Inferencer
from runtime.pipeline import load_model
from runtime.preview import *
from runtime.server import http_server, websocket_server
from runtime.storage import FrameCache, RecordingManager
from runtime.transform import Transforms

import argparse
import asyncio
import cv2
import functools
import json
import logging
import multiprocessing as mp
import numpy as np
import os.path as osp
import queue
import threading
import websockets


class PreviewFrameConsumer:
  def __call__(self, src_image, set_exit_cond, pipeline):
    image, result = pipeline(src_image)
    exit_cond = self.display(image, result)
    set_exit_cond(exit_cond)

  def __init__(self, **preview_config):
    self.pv_mode = preview_config['pv_mode']
    self.pv_window = preview_config['pv_window']
    self.pv_items = preview_config['pv_items']
    self.pv_size = preview_config['pv_size']

  def __enter__(self):
    if self.pv_mode == 'full':
      cv2.namedWindow(self.pv_window, cv2.WND_PROP_FULLSCREEN)
      cv2.setWindowProperty(self.pv_window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    if self.pv_mode == 'frame':
      cv2.namedWindow(self.pv_window, cv2.WND_PROP_AUTOSIZE)

  def __exit__(self, exc_type, exc_val, exc_tb):
    if self.pv_mode != 'none':
      cv2.destroyWindow(self.pv_window)

  def display(self, image, result):
    background = np.zeros(shape=self.pv_size + [3], dtype=np.uint8)
    canvas = create_pv_canvas(image, background, self.pv_mode, self.pv_items)

    if result['success']: # Display extra information on the preview
      if result['pog_scn'] is not None:
        display_gaze_on_canvas(canvas, result['pog_scn'], self.pv_mode, self.pv_items)
      display_time_on_canvas(canvas, result['time'], self.pv_mode, self.pv_items)
    else:
      display_warning_on_canvas(canvas, self.pv_mode, self.pv_items)

    return display_canvas(self.pv_window, canvas, self.pv_mode, self.pv_items)

class ServerFrameConsumer:
  def __call__(self, src_image, set_exit_cond, pipeline):
    result = pipeline(src_image)
    exit_cond = self.process(src_image, result)
    set_exit_cond(exit_cond)

  def __init__(self, open_event, kill_event, sync_result, record_info):
    self.open_event = open_event
    self.kill_event = kill_event

    self.sync_result = sync_result
    self.record_info = record_info

    self.frame_count = 0

  def __enter__(self):
    self.open_event.set() # Notify the parent process (websocket server, blocking)

    if self.record_info['enable']:
      self.frame_cache = FrameCache(self.record_info['cache_size'])
      self.rec_manager = RecordingManager(self.record_info['root'])
      self.rec_manager.new_recording(self.record_info['name'])

  def __exit__(self, exc_type, exc_val, exc_tb):
    if self.record_info['enable']:
      while not self.record_info['save_queue'].empty():
        self.save_frame_in_queue(self.record_info['save_queue'])

  def process(self, src_image, result):
    self.sync_result(result, self.frame_count)

    if self.record_info['enable']:
      self.frame_cache.insert_frame(src_image, self.frame_count)
      if not self.record_info['save_queue'].empty():
        self.save_frame_in_queue(self.record_info['save_queue'])

    self.frame_count += 1

    return self.kill_event.is_set()

  def save_frame_in_queue(self, save_queue):
    try:  # Fetch save task from save queue
      result_item = save_queue.get(timeout=0.01)
      fetched_item = self.frame_cache.fast_fetch(result_item['fid'])

      if fetched_item is not None:
        self.rec_manager.save_frame(
          fetched_item,
          result_item['gx'], result_item['gy'],
          result_item['lx'], result_item['ly'],
        )

    except queue.Empty:
      pass  # Nothing to save


def create_server_consumer(es_config, record_info, open_event, kill_event,
                           next_ready, next_valid, value_bank, value_lock):
  '''Run camera process and send the estimated PoG to the client.'''

  def sync_result(result, frame_count):
    with value_lock:
      if result['success'] and result['pog_scn'] is not None:
        value_bank[0] = result['pog_cam'][0]  # Gaze: x
        value_bank[1] = result['pog_cam'][1]  # Gaze: y
        next_valid.value = True     # PoG: valid
      else:
        next_valid.value = False

      value_bank[2] = frame_count   # Fid: frame
    next_ready.set()

  capture_builder = VideoCaptureBuilder(**EsConfigFns.named_dict(es_config, 'capture'))
  consumer = ServerFrameConsumer(open_event, kill_event, sync_result, record_info)

  if EsConfigFns.record_without_inference(es_config):
    def pipeline(src_image):
      return dict(success=False)

    with consumer:
      capture_handler = CaptureHandler(capture_builder, consumer)
      capture_handler.main_loop(pipeline=pipeline)

  else:
    config_path = EsConfigFns.get_config_path(es_config)
    model = load_model(config_path, **EsConfigFns.named_dict(es_config, 'checkpoint'))

    transforms = Transforms(**EsConfigFns.named_dict(es_config, 'transform'))
    alignment = FaceAlignment(**EsConfigFns.named_dict(es_config, 'alignment'))
    inferencer = Inferencer(**EsConfigFns.named_dict(es_config, 'inference'))

    def pipeline(src_image):
      image = transforms.transform(src_image)
      return inferencer.run(model, alignment, image)

    with alignment, consumer:
      capture_handler = CaptureHandler(capture_builder, consumer)
      capture_handler.main_loop(pipeline=pipeline)

def clean_up_context(context):
  if context.get('camera_proc', None):
    context['camera_kill'].set()
    context['camera_proc'].join()
  context.clear()

async def websocket_send_json(websocket, message_obj):
  '''Send a JSON object over websocket.'''
  await websocket.send(json.dumps(message_obj))

async def send_server_hello(websocket, es_config: EsConfig):
  message_obj = dict(status='server_on')

  message_obj['topleft_offset'] = EsConfigFns.topleft_offset(es_config)
  message_obj['screen_size_cm'] = EsConfigFns.screen_size_cm(es_config)
  message_obj['record_mode'] = EsConfigFns.record_mode(es_config)
  message_obj['game_settings'] = EsConfigFns.collect_game_settings(es_config)

  await websocket_send_json(websocket, message_obj)

async def send_gaze_predict(websocket, context):
  if context.get('camera_proc', None) and context['next_ready'].is_set():
    with context['value_lock']:
      # Sync value and status from the server consumer
      gx, gy, fid = context['value_bank'][:]
      next_valid = context['next_valid'].value
    context['next_ready'].clear()

    message_obj = dict(status='next_ready', valid=next_valid, fid=fid)
    if next_valid:
      message_obj.update(dict(gx=gx, gy=gy))

    await websocket_send_json(websocket, message_obj)

async def recv_client_message(websocket):
  exit_cond = False

  try:  # Wait for the message until a timeout occurs
    message = await asyncio.wait_for(websocket.recv(), timeout=0.01)
  except websockets.ConnectionClosed:
    exit_cond = True
  except asyncio.TimeoutError:
    message = None

  return exit_cond, message

async def on_open_camera(message_obj, websocket, context, es_config):
  context['camera_open'] = mp.Event()
  context['camera_kill'] = mp.Event()

  context['next_ready'] = mp.Event()
  context['next_valid'] = mp.Value('b', False)
  context['value_bank'] = mp.Array('d', (0.0, 0.0, 0.0))
  context['value_lock'] = mp.Lock()

  if EsConfigFns.record_mode(es_config):
    context['save_queue'] = mp.Queue()
    record_info = dict(
      enable=True, cache_size=600,
      root=EsConfigFns.record_path(es_config),
      name=message_obj.get('record_name', ''),
      save_queue=context['save_queue'],
    )
  else:
    record_info = dict(enable=False)

  context['camera_proc'] = mp.Process(
    target=create_server_consumer,
    args=(es_config, record_info),
    kwargs=dict(
      open_event=context['camera_open'],
      kill_event=context['camera_kill'],
      next_ready=context['next_ready'],
      next_valid=context['next_valid'],
      value_bank=context['value_bank'],
      value_lock=context['value_lock'],
    ),
  )

  context['camera_proc'].start()
  context['camera_open'].wait()

  await websocket_send_json(websocket, { 'status': 'camera_on' })

  return False

async def on_kill_camera(message_obj, websocket, context):
  clean_up_context(context)

  if not message_obj['hard']:
    await websocket_send_json(websocket, { 'status': 'camera_off' })

  return True

async def on_kill_server(message_obj, websocket, context, stop_future):
  clean_up_context(context)

  stop_future.set_result(True)

  return True

async def on_save_result(message_obj, websocket, context, es_config):
  if EsConfigFns.record_mode(es_config):
    # Item: frame id, gaze x, gaze y, label x, label y
    context['save_queue'].put(message_obj['result'])

  return False

async def websocket_handler(websocket, stop_future, es_config: EsConfig):
  '''Handler for incoming websocket requests, sent by main game loop.'''

  server_alive, exit_cond_1, exit_cond_2 = True, False, False

  await send_server_hello(websocket, es_config)

  handler_infos = dict(
    open_camera=dict(fn=on_open_camera, kw=dict(es_config=es_config)),
    kill_camera=dict(fn=on_kill_camera, kw=dict()),
    kill_server=dict(fn=on_kill_server, kw=dict(stop_future=stop_future)),
    save_result=dict(fn=on_save_result, kw=dict(es_config=es_config)),
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



def run_http_server(httpd):
  '''Http server thread that runs the preconfigured http server.'''

  with httpd:
    try:  # Serve incoming requests
      httpd.serve_forever()
    except KeyboardInterrupt:
      pass  # Exit on received Ctrl-C
    finally:
      httpd.server_close()

def run_websocket_server(ws_handler, httpd, host, port):
  '''Websocket server thread that runs the camera process on the backend.'''

  try:  # Run websocket server until gracefully terminated
    asyncio.run(websocket_server(ws_handler, host, port))
  except KeyboardInterrupt:
    pass  # Ignore traceback if no websocket handler is running

  httpd.shutdown()



def entry_server_mode(config_path):
  '''Serve the eye shooting game, until interrupted or stopped.'''

  content_root = osp.join(osp.dirname(osp.dirname(__file__)), 'sketch')

  es_config = EsConfig.from_toml(config_path)
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

def entry_preview_mode(config_path):
  '''Run camera process and preview the estimated PoG on the screen.'''

  es_config = EsConfig.from_toml(config_path)

  capture_builder = VideoCaptureBuilder(**EsConfigFns.named_dict(es_config, 'capture'))
  consumer = PreviewFrameConsumer(**EsConfigFns.named_dict(es_config, 'preview'))

  model = load_model(config_path, **EsConfigFns.named_dict(es_config, 'checkpoint'))

  transforms = Transforms(**EsConfigFns.named_dict(es_config, 'transform'))
  alignment = FaceAlignment(**EsConfigFns.named_dict(es_config, 'alignment'))
  inferencer = Inferencer(**EsConfigFns.named_dict(es_config, 'inference'))

  def pipeline(src_image):
    image = transforms.transform(src_image)
    result = inferencer.run(model, alignment, image)
    return image, result

  with alignment, consumer:
    capture_handler = CaptureHandler(capture_builder, consumer)
    capture_handler.main_loop(pipeline=pipeline)

MAIN_ENTRIES = dict(preview=entry_preview_mode, server=entry_server_mode)



def configure_logging(level=logging.INFO, force=False):
  logging.basicConfig(
    level=level, force=force,
    format='[ %(asctime)s ] process %(process)d - %(levelname)s: %(message)s',
    datefmt='%m-%d %H:%M:%S',
  )

def main_procedure(cmdargs: argparse.Namespace):
  entry = MAIN_ENTRIES.get(cmdargs.mode, None)
  config_path = osp.abspath(cmdargs.config)
  if entry is not None: entry(config_path)



if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Predict gaze point from trained model.')

  parser.add_argument('--config', type=str, default='estimator.toml',
                      help='Configuration for this PoG estimator.')
  parser.add_argument('--mode', type=str, default='server', choices=['server', 'preview'],
                      help='The mode to run the PoG estimator. Default is server.')

  configure_logging(logging.INFO, force=True)
  main_procedure(parser.parse_args())
