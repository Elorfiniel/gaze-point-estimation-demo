from .one_euro import OneEuroFilter
from .pipeline import (
  prepare_model_input,
  rotate_vector_a,
  do_model_inference,
)

import cv2
import functools
import numpy as np
import time


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

def predict_model_output(model, crops, norm_ldmks, face_resize, eyes_resize):
  # Prepare model input according to model type
  face_crop, reye_crop, leye_crop = crops
  reye_center, leye_center = norm_ldmks[468], norm_ldmks[473]
  eye_ldmks = np.concatenate([reye_center, leye_center])

  model_input = prepare_model_input(face_crop, reye_crop, leye_crop, eye_ldmks,
                                    face_resize, eyes_resize)
  ort_outputs = do_model_inference(model, model_input)

  return ort_outputs

def predict_screen_xy(model, crops, norm_ldmks, theta,
                      topleft_offset, screen_size_px, screen_size_cm,
                      face_resize, eyes_resize, gx_filter, gy_filter):
  ort_outputs = predict_model_output(model, crops, norm_ldmks, face_resize, eyes_resize)

  # Gaze point predicted by model should be projected from prediction space
  # back into camera coordinate space, by rotating around origin with `theta`
  #   gx, gy = rotate_vector_a(gcx, gcy, theta).tolist()
  gcx, gcy = ort_outputs[0].squeeze(0).tolist()
  gaze_vec = rotate_vector_a(gcx, gcy, theta)

  # Display predicted gaze point on the screen
  gaze_screen_xy = gaze_vec_to_screen_xy(gaze_vec, topleft_offset,
                                         screen_size_px, screen_size_cm)
  if gaze_screen_xy is not None:
    gx = gx_filter.filter(gaze_screen_xy[0])
    gy = gy_filter.filter(gaze_screen_xy[1])
    gx = clamp_with_converter(gx, 0, screen_size_px[1], converter=int)
    gy = clamp_with_converter(gy, 0, screen_size_px[0], converter=int)
    gaze_screen_xy = (gx, gy)

  return gaze_screen_xy, gaze_vec


class Inferencer:
  def __init__(self, topleft_offset, screen_size_px, screen_size_cm,
               face_resize=(224, 224), eyes_resize=(224, 224),
               gx_filt_params=dict(), gy_filt_params=dict()):
    '''Initailize inference pipeline with device specific parameters.

    `topleft_offset`: offset of screen topleft corner in camera coordinate system.

    `screen_size_px`: screen size (height, weight) in pixels.

    `screen_size_cm`: screen size (height, weight) in centimeters.

    `face_resize`: resize input face image for estimator.

    `eyes_resize`: resize input eye images for estimator.

    `gx_filt_params`: parameters for one-euro filter along x-axis.

    `gy_filt_params`: parameters for one-euro filter along y-axis.
    '''

    self.hw_ratio = eyes_resize[1] / eyes_resize[0]
    self.predict_fn = functools.partial(
      predict_screen_xy,
      topleft_offset=topleft_offset,
      screen_size_px=screen_size_px,
      screen_size_cm=screen_size_cm,
      face_resize=face_resize,
      eyes_resize=eyes_resize,
    )
    self.gx_filter = OneEuroFilter(**gx_filt_params)
    self.gy_filter = OneEuroFilter(**gy_filt_params)

  def run(self, model, align, image, to_rgb=True):
    '''Run inference with model on the aligned image.

    Returns a result dictionary with the following keys:
      success: bool, whether the inference was successful.
      pog_scn: filtered PoG (x, y) in screen coordinate frame.
      pog_cam: non-filtered PoG (x, y) in camera coordinate frame.
      time: inference time in seconds.

    Note that pog_scn and pog_cam are returned only on success.
    '''

    result = dict(success=False)
    inference_start = time.time()

    if to_rgb: image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    landmarks, theta = align.process(image)
    if len(landmarks) > 0:
      crops, norm_ldmks, _ = align.get_face_crop(
        image, landmarks, theta, hw_ratio=self.hw_ratio,
      )
      pog_scn, pog_cam = self.predict_fn(
        model, crops, norm_ldmks, theta,
        gx_filter=self.gx_filter, gy_filter=self.gy_filter,
      )

      inference_finish = time.time()
      result.update(dict(
        success=True, pog_scn=pog_scn, pog_cam=pog_cam,
        time=inference_finish - inference_start,
      ))

    return result
