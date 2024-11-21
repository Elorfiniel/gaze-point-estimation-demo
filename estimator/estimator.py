from runtime.facealign import FaceAlignment
from runtime.inference import predict_screen_xy
from runtime.miscellaneous import *
from runtime.one_euro import OneEuroFilter
from runtime.pipeline import load_model
from runtime.preview import *
from runtime.storage import FrameCache, RecordingManager

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
import time
import websockets


def fetch_save_task(save_queue, frame_cache, recording_manager):
  try:  # Fetch save task from save queue
    tid, px, py, lx, ly = save_queue.get(timeout=0.01)
    fetched_item = frame_cache.fast_fetch(tid)

    if fetched_item is not None:
      recording_manager.save_frame(fetched_item, px, py, lx, ly)

  except queue.Empty:
    pass  # Nothing to save

def camera_handler(model, camera_id,
                   topleft_offset, screen_size_px, screen_size_cm,
                   capture_resolution, target_resolution,
                   face_resize=(224, 224), eyes_resize=(224, 224),
                   pv_mode='none', pv_window='preview',
                   pv_items=['frame', 'gaze', 'time', 'warn'],
                   gx_filt_params=dict(), gy_filt_params=dict(),
                   server_params=None, **extra_kwargs):
  server_mode = server_params is not None and isinstance(server_params, dict)

  if server_mode:
    frame_count = 0

    if server_params['record_path']:
      # Create a recording manager to save captured frames
      frame_cache = FrameCache(max_count=600)
      recording_manager = RecordingManager(root=server_params['record_path'])

  # Create a video capture for the specified camera id
  capture = cv2.VideoCapture(camera_id)
  capture.set(cv2.CAP_PROP_FRAME_HEIGHT, capture_resolution[0])
  capture.set(cv2.CAP_PROP_FRAME_WIDTH, capture_resolution[1])

  # Prepare blank background for preview
  background = None
  if pv_mode == 'full':
    background = np.zeros(shape=screen_size_px + [3], dtype=np.uint8)
    cv2.namedWindow(pv_window, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(pv_window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
  if pv_mode == 'frame':
    cv2.namedWindow(pv_window, cv2.WND_PROP_AUTOSIZE)

  # Initialize location filters for the predicted point of gaze
  gx_filter = OneEuroFilter(**gx_filt_params)
  gy_filter = OneEuroFilter(**gy_filt_params)

  # Initialize mediapipe pipeline for face mesh detection
  alignment = FaceAlignment(static_image_mode=False, min_detection_confidence=0.80)

  # [Warn] Normally, the camera will be opened correctly, check this on failure
  logging.info(f'camera id {camera_id}, camera is opened {capture.isOpened()}')

  # Notify the parent process (websocket server, blocking)
  if server_mode:
    server_params['open_event'].set()

  while (not server_params['kill_event'].is_set() if server_mode else True):
    success, source_image = capture.read()
    if not success: continue

    # measure clock for all inference steps
    inference_start = time.time()

    image = shrink_frame(source_image, capture_resolution, target_resolution)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    landmarks, theta = alignment.process(rgb_image)

    canvas = create_pv_canvas(image, background, pv_mode, pv_items)

    gaze_screen_xy = None # Reset before next prediction

    if len(landmarks) > 0:
      # Get face crop, eye crops and face landmarks
      hw_ratio = eyes_resize[1] / eyes_resize[0]
      crops, norm_ldmks, new_ldmks = alignment.get_face_crop(
        rgb_image, landmarks, theta, hw_ratio=hw_ratio)
      # Inference: predict PoG on the screen
      gaze_screen_xy, gaze_vec = predict_screen_xy(
        model, crops, norm_ldmks, face_resize, eyes_resize,
        theta, topleft_offset, screen_size_px, screen_size_cm,
        gx_filter, gy_filter,
      )

      # measure clock for all inference steps
      inference_finish = time.time()
      inference_time = inference_finish - inference_start

      # Display extra information on the preview
      if gaze_screen_xy is not None:
        display_gaze_on_canvas(canvas, gaze_screen_xy, pv_mode, pv_items)
      display_time_on_canvas(canvas, inference_time, pv_mode, pv_items)

    else:
      display_warning_on_canvas(canvas, pv_mode, pv_items)

    if server_mode:
      # Save the latest PoG inside the shared array
      with server_params['value_lock']:
        if gaze_screen_xy is not None:
          server_params['value_bank'][0] = gaze_vec[0] # Gaze: x
          server_params['value_bank'][1] = gaze_vec[1] # Gaze: y
          server_params['next_valid'].value = True     # PoG: valid
        else:
          server_params['next_valid'].value = False

        server_params['value_bank'][2] = frame_count   # Tid: frame
      server_params['next_ready'].set()

      if server_params['record_path']:
        frame_cache.insert_frame(source_image, frame_count)
      frame_count += 1

    if display_canvas(pv_window, canvas, pv_mode, pv_items): break

    if server_mode:
      # Save the captured frame on disk, if any
      if server_params['record_path'] and not server_params['save_queue'].empty():
        fetch_save_task(server_params['save_queue'], frame_cache, recording_manager)

  # Destroy named windows used for preview
  if pv_mode != 'none':
    cv2.destroyAllWindows()

  alignment.close()
  capture.release()

  if server_mode:
    # Flush the remaining save task inside the save queue
    while server_params['record_path'] and not server_params['save_queue'].empty():
      fetch_save_task(server_params['save_queue'], frame_cache, recording_manager)

def camera_process(config, record_path, save_queue,
                   open_event, kill_event, value_bank, value_lock,
                   next_ready, next_valid):
  '''Load model using configuration, start the camera handler.'''

  logging.info('gaze point estimator will start in a few seconds')

  # Load estimator checkpoint from file system
  config = config.copy()  # Prevent modification
  model = load_model(config.pop('__config_path'), config.pop('checkpoint'))

  # Handle control to camera handler
  server_params = dict(
    open_event=open_event,
    kill_event=kill_event,
    value_bank=value_bank,
    value_lock=value_lock,
    next_ready=next_ready,
    next_valid=next_valid,
    record_path=record_path,
    save_queue=save_queue,
  )
  camera_handler(model, **config, server_params=server_params)

  logging.info('gaze point estimator has been safely closed, now terminating')



async def server_hello(websocket, config, record_mode, game_settings):
  # Send "server-on" to notify the client
  await websocket_send_json(websocket, {
    'status': 'server-on',
    'topleftOffset': config['topleft_offset'],
    'screenSizeCm': config['screen_size_cm'],
    'recordMode': record_mode,
    'gameSettings': game_settings,
  })

async def handle_message(message, websocket, camera_status, **kwargs):
  logging.debug(f'websocket server received message - {message}')

  should_exit = False
  message_obj = json.loads(message)

  # On receving "open-cam", start the camera process
  if message_obj['opcode'] == 'open-cam':
    camera_status['camera-open'] = mp.Event()
    camera_status['camera-kill'] = mp.Event()
    camera_status['next-ready'] = mp.Event()
    camera_status['next-valid'] = mp.Value('b', False)
    camera_status['value-bank'] = mp.Array('d', (0.0, 0.0, 0.0))
    camera_status['value-lock'] = mp.Lock()
    camera_status['save-queue'] = mp.Queue()

    camera_status['camera-proc'] = mp.Process(
      target=camera_process, args=(
        kwargs['config'],
        kwargs['record_path'],
        camera_status['save-queue'],
        camera_status['camera-open'],
        camera_status['camera-kill'],
        camera_status['value-bank'],
        camera_status['value-lock'],
        camera_status['next-ready'],
        camera_status['next-valid'],
      ),
    )

    camera_status['camera-proc'].start()
    camera_status['camera-open'].wait()

    # Send "camera-on" to notify the client
    await websocket_send_json(websocket, { 'status': 'camera-on' })

  # On receiving "kill-cam", terminate the camera process
  # On receiving "kill-server", terminate the server
  if message_obj['opcode'] in ['kill-cam', 'kill-server']:
    if camera_status.get('camera-proc', None):
      camera_status['camera-kill'].set()
      camera_status['camera-proc'].join()

    camera_status.clear()

    if message_obj['opcode'] == 'kill-cam':
      if not message_obj['hard']:
        # Send "camera-off" to notify the client
        await websocket_send_json(websocket, { 'status': 'camera-off' })

    if message_obj['opcode'] == 'kill-server':
      kwargs['stop_future'].set_result(True)

    should_exit = True

  # On receiving "save-gaze", enqueue label in the save task queue
  if message_obj['opcode'] == 'save-gaze':
    camera_status['save-queue'].put((
      message_obj['tid'],
      message_obj['gaze_x'],
      message_obj['gaze_y'],
      message_obj['label_x'],
      message_obj['label_y'],
    ))

  return should_exit

async def broadcast_gaze(websocket, camera_status):
  if camera_status['next-ready'].is_set():
    with camera_status['value-lock']:
      # Sync value and status from the camera process
      gaze_x, gaze_y, tid = camera_status['value-bank'][:]
      next_valid = camera_status['next-valid'].value
    camera_status['next-ready'].clear()

    message_obj = {'status': 'next-ready', 'valid': next_valid, 'tid': tid}
    if next_valid:
      message_obj.update({'gaze_x': gaze_x, 'gaze_y': gaze_y})

    # Send "next-ready" to notify the client
    await websocket_send_json(websocket, message_obj)

async def server_process(websocket, stop_future, config_path, record_mode, record_path):
  logging.info('websocket server started, listening for requests')
  logging.info(f'loading estimator configuration from {config_path}')
  if record_mode:
    logging.info(f'recording mode on, save recordings to {record_path}')
  record_path = osp.abspath(record_path) if record_mode else ''

  # Load configuration for the PoG estimator
  config = load_toml_secure(config_path)
  config['__config_path'] = config_path

  # Send "server-on" packet to notify the client
  await server_hello(websocket, config, record_mode, config.pop('game_settings'))

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



async def websocket_server(ws_handler, host, port):
  '''A general-purpose websocket server that runs forever.'''

  loop = asyncio.get_running_loop()
  stop = loop.create_future()

  ws_handler = functools.partial(ws_handler, stop_future=stop)

  async with websockets.serve(ws_handler, host, port):
    await stop  # Run until stop future is resolved



def main_procedure_server(cmdargs: argparse.Namespace):
  '''Start a camera process and a server process, run until interrupted.'''

  logging.info('starting the websocket server to listen for client requests')

  ws_handler = functools.partial(
    server_process,
    config_path=cmdargs.config,
    record_mode=cmdargs.record_mode,
    record_path=cmdargs.record_path,
  )

  try:  # Run websocket server until gracefully terminated
    asyncio.run(websocket_server(ws_handler, cmdargs.host, cmdargs.port))
  except KeyboardInterrupt:
    pass  # Ignore traceback if no websocket handler is running

  logging.info('websocket finished execution, now exiting')

def main_procedure_preview(cmdargs: argparse.Namespace):
  '''Run camera process and preview the estimated PoG on the screen.'''

  logging.info('gaze point estimator preview will start in a few seconds')

  # Load configuration for the PoG estimator
  config_path = osp.abspath(cmdargs.config)
  config = load_toml_secure(config_path)
  # Load estimator checkpoint from file system
  model = load_model(config_path, config.pop('checkpoint'))
  # Drop extra kwargs used in server mode
  config.pop('game_settings', None)
  # Handle control to camera preview
  camera_handler(model, **config)

  logging.info('gaze point estimator preview finished, now exiting')

def main_procedure(cmdargs: argparse.Namespace):
  if cmdargs.mode == 'server':
    main_procedure_server(cmdargs)

  if cmdargs.mode == 'preview':
    main_procedure_preview(cmdargs)



if __name__ == '__main__':
  configure_logging(logging.INFO, force=True)

  parser = argparse.ArgumentParser(description='Predict gaze point from trained model.')

  parser.add_argument('--config', type=str, default='estimator.toml',
                      help='Configuration for this PoG estimator.')
  parser.add_argument('--mode', type=str, default='server', choices=['server', 'preview'],
                      help='The mode to run the PoG estimator. Default is server.')

  parser.add_argument('--host', type=str, default='localhost',
                      help='The host address to bind the server to. Default is localhost.')
  parser.add_argument('--port', type=int, default=4200,
                      help='The port number to bind the server to. Default is 4200.')

  parser.add_argument('--record-mode', default=False, action='store_true',
                      help='Enable recording mode. Default is False.')
  parser.add_argument('--record-path', type=str, default='demo-capture',
                      help='The path to store the recordings. Default is "demo-capture".')

  main_procedure(parser.parse_args())
