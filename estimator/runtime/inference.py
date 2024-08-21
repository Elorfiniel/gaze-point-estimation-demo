from runtime.pipeline import (
  prepare_model_input,
  rotate_vector_a,
  do_model_inference,
)

import numpy as np


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

def predict_screen_xy(model, crops, norm_ldmks, face_resize, eyes_resize,
                      theta, topleft_offset, screen_size_px, screen_size_cm,
                      gx_filter, gy_filter):
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
