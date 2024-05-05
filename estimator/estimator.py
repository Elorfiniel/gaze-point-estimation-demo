from runtime.facealign import FaceAlignment
from runtime.miscellaneous import *
from runtime.one_euro import OneEuroFilter
from runtime.pipeline import load_model
from runtime.preview import *
from runtime.inference import predict_screen_xy

from argparse import ArgumentParser, Namespace

import asyncio
import cv2, json
import multiprocessing
import numpy as np
import websockets


def run_model_on_camera(mp_context, mp_context_lock,
                        model, camera_id,
                        topleft_offset, screen_size_px, screen_size_cm,
                        face_resize=(224, 224), eyes_resize=(224, 224),
                        pv_mode='none', pv_window='preview',
                        pv_items=['frame', 'gaze', 'time', 'warn'],
                        gx_filt_params=dict(), gy_filt_params=dict()):
  # Create a video capture for the specified camera id
  capture = cv2.VideoCapture(camera_id)

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

  with FaceAlignment(static_image_mode=False,
                     min_detection_confidence=0.80) as alignment:
    while capture.isOpened():
      success, image = capture.read()
      if not success: continue

      rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
      landmarks, theta = alignment.process(rgb_image)

      canvas = create_pv_canvas(image, background, pv_mode, pv_items)

      if len(landmarks) > 0:
        # Get face crop, eye crops and face landmarks
        hw_ratio = eyes_resize[1] / eyes_resize[0]
        crops, norm_ldmks, new_ldmks = alignment.get_face_crop(
          rgb_image, landmarks, theta, hw_ratio=hw_ratio)
        # Inference: predict PoG on the screen
        gaze_screen_xy, inference_time = predict_screen_xy(
          model, crops, norm_ldmks, face_resize, eyes_resize,
          theta, topleft_offset, screen_size_px, screen_size_cm,
          gx_filter, gy_filter,
        )
        # Save the latest PoG inside the shared array
        if gaze_screen_xy is not None:
          with mp_context_lock:
            mp_context.gx, mp_context.gy = gaze_screen_xy

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

  capture.release()

def run_estimator(mp_context, mp_context_lock, config_path):
  '''Generate predicted point of gaze on the screen.
  '''

  # Load configuration for the PoG estimator
  config = load_toml_secure(config_path)
  # Load estimator checkpoint from file system
  model = load_model(config_path, config.pop('checkpoint'))

  run_model_on_camera(mp_context, mp_context_lock, model, **config)


def run_server(mp_context, mp_context_lock, host='localhost', port=4200):
  '''Make response to the client according to the transmission API.
  '''

  # Make response: handle requests from the client
  async def make_response(websocket):
    async for message in websocket:
      request = json.loads(message)

      if request['action'] == 'gaze':
        with mp_context_lock:
          screen_xy = [mp_context.gx, mp_context.gy]
          response = json.dumps(screen_xy)
        await websocket.send(response)

  # Start response loop: the websocket server
  async def websocket_server():
    async with websockets.serve(make_response, host, port):
      await asyncio.Future()  # Run forever

  # Start the websocket server
  asyncio.run(websocket_server())


def main_procedure(cmdargs: Namespace):
  '''Start a camera process and a server process, run until interrupted.
  '''

  configure_logging(logging.DEBUG, force=True)
  logging.info('starting a camera process and a server process ...')

  with multiprocessing.Manager() as manager:
    mp_context = manager.Namespace()
    mp_context_lock = manager.Lock()

    with mp_context_lock:
      mp_context.gx, mp_context.gy = 0, 0

    estimator = multiprocessing.Process(
      target=run_estimator,
      args=(mp_context, mp_context_lock, cmdargs.config),
    )
    estimator.start()

    server = multiprocessing.Process(
      target=run_server,
      args=(mp_context, mp_context_lock, cmdargs.host, cmdargs.port),
    )
    server.start()

    estimator.join()
    server.join()

  logging.info('finishing execution, now exiting ...')



if __name__ == '__main__':
  parser = ArgumentParser(description='Predict gaze point from trained model.')

  parser.add_argument('--config', type=str, default='estimator.toml',
                      help='Configuration for this PoG estimator.')

  parser.add_argument('--host', type=str, default='localhost',
                      help='The host address to bind the server to. Default is localhost.')
  parser.add_argument('--port', type=int, default=4200,
                      help='The port number to bind the server to. Default is 4200.')

  main_procedure(parser.parse_args())
