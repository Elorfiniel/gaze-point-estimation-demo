from runtime.facealign import FaceAlignment
from runtime.inference import predict_screen_xy
from runtime.miscellaneous import *
from runtime.one_euro import OneEuroFilter
from runtime.pipeline import load_model
from runtime.preview import *
from runtime.storage import FrameCache, RecordingManager

from argparse import ArgumentParser, Namespace

import asyncio
import functools
import cv2
import json
import multiprocessing
import numpy as np
import os.path as osp
import queue
import websockets


def camera_handler(open_event, kill_event, value_bank, value_lock, gaze_ready,
                   record_path, save_queue,
                   model, camera_id,
                   topleft_offset, screen_size_px, screen_size_cm,
                   capture_resolution, target_resolution,
                   face_resize=(224, 224), eyes_resize=(224, 224),
                   pv_mode='none', pv_window='preview',
                   pv_items=['frame', 'gaze', 'time', 'warn'],
                   gx_filt_params=dict(), gy_filt_params=dict()):
  frame_count = 0

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
  open_event.set()

  while not kill_event.is_set():
    success, source_image = capture.read()
    if not success: continue

    image = shrink_frame(source_image, capture_resolution, target_resolution)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    landmarks, theta = alignment.process(rgb_image)

    canvas = create_pv_canvas(image, background, pv_mode, pv_items)

    if len(landmarks) > 0:
      # Get face crop, eye crops and face landmarks
      hw_ratio = eyes_resize[1] / eyes_resize[0]
      crops, norm_ldmks, new_ldmks = alignment.get_face_crop(
        rgb_image, landmarks, theta, hw_ratio=hw_ratio)
      # Inference: predict PoG on the screen
      gaze_screen_xy, gaze_vec, inference_time = predict_screen_xy(
        model, crops, norm_ldmks, face_resize, eyes_resize,
        theta, topleft_offset, screen_size_px, screen_size_cm,
        gx_filter, gy_filter,
      )

      # Save the latest PoG inside the shared array
      if gaze_screen_xy is not None:
        with value_lock:
          value_bank[0] = gaze_vec[0] # Gaze: x
          value_bank[1] = gaze_vec[1] # Gaze: y
          value_bank[2] = frame_count # Tid: frame
        gaze_ready.set()

        frame_count += 1

      # Display extra information on the preview
      if gaze_screen_xy is not None:
        display_gaze_on_canvas(canvas, gaze_screen_xy, pv_mode, pv_items)
      display_time_on_canvas(canvas, inference_time, pv_mode, pv_items)

    else:
      display_warning_on_canvas(canvas, pv_mode, pv_items)

    if display_canvas(pv_window, canvas, pv_mode, pv_items): break

  # Destroy named windows used for preview
  if pv_mode != 'none':
    cv2.destroyAllWindows()

  alignment.close()
  capture.release()

def camera_process(config_path, record_path, save_queue,
                   open_event, kill_event, value_bank, value_lock, gaze_ready):
  '''Load model using configuration, start the camera handler.'''

  logging.info('gaze point estimator will start in a few seconds')

  # Load configuration for the PoG estimator
  config = load_toml_secure(config_path)
  # Load estimator checkpoint from file system
  model = load_model(config_path, config.pop('checkpoint'))
  # Handle control to camera handler
  camera_handler(
    open_event, kill_event, value_bank, value_lock, gaze_ready,
    record_path, save_queue, model, **config,
  )

  logging.info('gaze point estimator has been safely closed, now terminating')



async def server_hello(websocket, config_path, record_mode):
  # Load actual screen height and width from the PoG estimator configuration
  config = load_toml_secure(config_path)
  # Send "server-on" to notify the client
  await websocket_send_json(websocket, {
    'status': 'server-on',
    'topleftOffset': config['topleft_offset'],
    'screenSizePx': config['screen_size_px'],
    'screenSizeCm': config['screen_size_cm'],
    'recordMode': record_mode,
  })

async def handle_message(message, websocket, camera_status, config_path, record_path):
  logging.debug(f'websocket server received message - {message}')

  message_obj = json.loads(message)

  # On receving "open-cam", start the camera process
  if message_obj['opcode'] == 'open-cam':
    camera_status['camera-open'] = multiprocessing.Event()
    camera_status['camera-kill'] = multiprocessing.Event()
    camera_status['gaze-ready'] = multiprocessing.Event()
    camera_status['value-bank'] = multiprocessing.Array('d', (0.0, 0.0, 0.0))
    camera_status['value-lock'] = multiprocessing.Lock()
    camera_status['save-queue'] = multiprocessing.Queue()

    camera_status['camera-proc'] = multiprocessing.Process(
      target=camera_process, args=(
        config_path, record_path,
        camera_status['save-queue'],
        camera_status['camera-open'],
        camera_status['camera-kill'],
        camera_status['value-bank'],
        camera_status['value-lock'],
        camera_status['gaze-ready'],
      ),
    )

    camera_status['camera-proc'].start()
    camera_status['camera-open'].wait()

    # Send "camera-on" to notify the client
    await websocket_send_json(websocket, { 'status': 'camera-on' })

  # On receiving "kill-cam", terminate the camera process
  if message_obj['opcode'] == 'kill-cam':
    camera_status['camera-kill'].set()
    camera_status['camera-proc'].join()
    camera_status.clear()

    # Send "camera-off" to notify the client
    await websocket_send_json(websocket, { 'status': 'camera-off' })

async def broadcast_gaze(websocket, camera_status):
  if camera_status['gaze-ready'].is_set():
    with camera_status['value-lock']:
      gaze_x, gaze_y, tid = camera_status['value-bank'][:]
    camera_status['gaze-ready'].clear()

    # Send "gaze-ready" to notify the client
    await websocket_send_json(websocket, {
      'status': 'gaze-ready',
      'gaze_x': gaze_x, 'gaze_y': gaze_y, 'tid': tid,
    })

async def server_process(websocket, config_path, record_mode, record_path):
  logging.info('websocket server started, listening for requests')
  logging.info(f'loading estimator configuration from {config_path}')
  if record_mode:
    logging.info(f'recording mode on, save recordings to {record_path}')
  record_path = osp.abspath(record_path) if record_mode else ''

  # Send "server-on" to notify the client
  await server_hello(websocket, config_path, record_mode)

  camera_status = {}

  while True:
    try:  # Wait for the message until a timeout occurs
      message = await asyncio.wait_for(websocket.recv(), timeout=0.01)
    except websockets.ConnectionClosed:
      break # Close server upon closed client
    except asyncio.TimeoutError:
      message = None

    if message is not None:
      await handle_message(message, websocket, camera_status, config_path, record_path)

    if camera_status.get('camera-proc', None):
      await broadcast_gaze(websocket, camera_status)

  logging.info('websocket server closed, waiting for next new request')



async def websocket_server(ws_handler, host, port):
  '''A general-purpose websocket server that runs forever.'''

  async with websockets.serve(ws_handler, host, port):
    await asyncio.Future()  # Run forever



def main_procedure(cmdargs: Namespace):
  '''Start a camera process and a server process, run until interrupted.'''

  configure_logging(logging.INFO, force=True)
  logging.info('starting the websocket server to listen for client requests')

  ws_handler = functools.partial(
    server_process,
    config_path=cmdargs.config,
    record_mode=cmdargs.record_mode,
    record_path=cmdargs.record_path,
  )
  asyncio.run(websocket_server(ws_handler, cmdargs.host, cmdargs.port))

  logging.info('websocket finished execution, now exiting')



if __name__ == '__main__':
  parser = ArgumentParser(description='Predict gaze point from trained model.')

  parser.add_argument('--config', type=str, default='estimator.toml',
                      help='Configuration for this PoG estimator.')

  parser.add_argument('--host', type=str, default='localhost',
                      help='The host address to bind the server to. Default is localhost.')
  parser.add_argument('--port', type=int, default=4200,
                      help='The port number to bind the server to. Default is 4200.')

  parser.add_argument('--record-mode', type=bool, default=False, action='store_true',
                      help='Enable recording mode. Default is False.')
  parser.add_argument('--record-path', type=str, default='demo-capture',
                      help='The path to store the recordings. Default is "demo-capture".')

  main_procedure(parser.parse_args())
