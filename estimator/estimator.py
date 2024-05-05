from runtime.facealign import FaceAlignment
from runtime.miscellaneous import *
from runtime.one_euro import OneEuroFilter
from runtime.pipeline import *
from runtime.preview import *

from argparse import ArgumentParser, Namespace
from datetime import datetime

import cv2, time
import numpy as np
import torch as torch


def clamp_with_converter(value, v_min, v_max, converter=None):
  clipped_v = value

  if value < v_min: clipped_v = v_min
  if value > v_max: clipped_v = v_max

  if converter:
    clipped_v = converter(clipped_v)

  return clipped_v

def gaze_vec_to_screen_xy(gaze_vector, screen_topleft_off_cm,
                          full_screen_size_px, full_screen_size_cm):
  gaze_pt = gaze_vector - np.array(screen_topleft_off_cm)
  gaze_pt[1] = -gaze_pt[1]  # Flip Y-axis

  if gaze_pt[0] > 0.0 and gaze_pt[0] < full_screen_size_cm[1]:
    if gaze_pt[1] > 0.0 and gaze_pt[1] < full_screen_size_cm[0]:
      gx_px = int(gaze_pt[0] / full_screen_size_cm[1] * full_screen_size_px[1])
      gy_px = int(gaze_pt[1] / full_screen_size_cm[0] * full_screen_size_px[0])
      return gx_px, gy_px

  return None


def run_model_on_camera(model, camera_id,
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
        # Get face and eye region crops, prepare model inputs
        hw_ratio = eyes_resize[1] / eyes_resize[0]
        crops, norm_ldmks, new_ldmks = alignment.get_face_crop(
          rgb_image, landmarks, theta, hw_ratio=hw_ratio)
        # Prepare model input according to model type
        face_crop, reye_crop, leye_crop = crops
        reye_center, leye_center = norm_ldmks[468], norm_ldmks[473]
        eye_ldmks = np.concatenate([reye_center, leye_center])

        model_input = prepare_model_input(face_crop, reye_crop, leye_crop, eye_ldmks,
                                          face_resize, eyes_resize)

        # Inference according to model type
        inference_start = time.time()
        gaze_vec = do_model_inference(model, model_input, theta)
        inference_finish = time.time()
        inference_time = inference_finish - inference_start

        # Display predicted gaze point on the screen
        gaze_screen_xy = gaze_vec_to_screen_xy(gaze_vec, topleft_offset,
                                               screen_size_px, screen_size_cm)
        if gaze_screen_xy is not None:
          gx = gx_filter.filter(gaze_screen_xy[0])
          gy = gy_filter.filter(gaze_screen_xy[1])
          gx = clamp_with_converter(gx, 0, screen_size_px[1], converter=int)
          gy = clamp_with_converter(gy, 0, screen_size_px[0], converter=int)

        if gaze_screen_xy is not None:
          display_gaze_on_canvas(canvas, gx, gy, pv_mode, pv_items)
        display_time_on_canvas(canvas, inference_time, pv_mode, pv_items)

      else:
        display_warning_on_canvas(canvas, pv_mode, pv_items)

      if display_canvas(pv_window, canvas, pv_mode, pv_items): break

  # Destroy named windows used for preview
  if pv_mode != 'none':
    cv2.destroyAllWindows()

  capture.release()


def main_procedure(cmdargs: Namespace):
  config = load_toml_secure(cmdargs.config)

  # Load estimator checkpoint from file system
  model = load_model(cmdargs.config, config.pop('checkpoint'))
  # Run inference with camera input stream
  run_model_on_camera(model=model, **config)

  print(f'finish execution at {datetime.now().strftime("%Y/%b/%d %H:%M")}')



if __name__ == '__main__':
  parser = ArgumentParser(description='Predict gaze point from trained model.')

  parser.add_argument('--config', type=str, default='estimator.toml',
                      help='Configuration for this PoG estimator.')

  main_procedure(parser.parse_args())
