from runtime.facealign import FaceAlignment
from runtime.miscellaneous import load_toml_secure
from runtime.one_euro import OneEuroFilter
from runtime.pipeline import load_model, prepare_model_input, do_model_inference

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

def run_camera(model,
               topleft_offset, screen_size_px, screen_size_cm,
               face_resize=(224, 224), eyes_resize=(224, 224),
               capturing_device_id = 0, cv2_window_name = 'Preview'):
  # Generate blank background for preview
  background = np.zeros(shape=screen_size_px + [3], dtype=np.uint8)

  capture = cv2.VideoCapture(capturing_device_id)
  cv2.namedWindow(cv2_window_name, cv2.WND_PROP_FULLSCREEN)
  cv2.setWindowProperty(cv2_window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

  gx_filter = OneEuroFilter(beta=0.01, min_cutoff=0.1, d_cutoff=1.2, clock=True)
  gy_filter = OneEuroFilter(beta=0.01, min_cutoff=0.1, d_cutoff=1.2, clock=True)

  with FaceAlignment(static_image_mode=False,
                     min_detection_confidence=0.80) as alignment:
    while capture.isOpened():
      success, image = capture.read()
      if not success: continue

      canvas = background.copy()  # Make a copy for drawing
      ph, pw, _ = image.shape
      tw = 320; th = int(tw * ph / pw)
      canvas[:th, :tw] = cv2.resize(image, (tw, th), interpolation=cv2.INTER_CUBIC)

      rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
      landmarks, theta = alignment.process(rgb_image)

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

          cv2.circle(canvas, (gx, gy), radius=56,
                     color=(0, 0, 255), thickness=4, lineType=cv2.LINE_AA)

        cv2.putText(canvas, f'Inference Time: {inference_time:.2f}s, FPS: {1.0 / inference_time:.2f}',
                    (50, screen_size_px[0] - 50), cv2.FONT_HERSHEY_PLAIN, 1.6,
                    color=(0, 0, 255), thickness=2, lineType=cv2.LINE_AA)

      else:
        cv2.putText(canvas, f'No face detected in the frame, anything wrong with the camera?',
                    (50, screen_size_px[0] - 50), cv2.FONT_HERSHEY_PLAIN, 1.6,
                    color=(0, 0, 255), thickness=2, lineType=cv2.LINE_AA)

      cv2.imshow(cv2_window_name, canvas)
      if cv2.waitKey(6) & 0xFF == ord('X'): break

  capture.release()
  cv2.destroyAllWindows()


def main_procedure(cmdargs: Namespace):
  config = load_toml_secure(cmdargs.config)

  # Load estimator checkpoint from file system
  model = load_model(cmdargs.config, config.pop('checkpoint'))
  # Run inference with camera input stream
  run_camera(model, **config)

  print(f'finish execution at {datetime.now().strftime("%Y/%b/%d %H:%M")}')



if __name__ == '__main__':
  parser = ArgumentParser(description='Predict gaze point from trained model.')

  parser.add_argument('--config', type=str, default='estimator.toml',
                      help='Configuration for this PoG estimator.')

  main_procedure(parser.parse_args())
