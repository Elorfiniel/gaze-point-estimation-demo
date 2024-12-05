from tool_utils import (
  active_root_logger,
  parse_file_ext, parse_key_value,
  update_kwargs_by_pop,
  resolve_estimator_runtime_path,
)

from sklearn.compose import TransformedTargetRegressor
from sklearn.kernel_ridge import KernelRidge
from sklearn.linear_model import HuberRegressor, Ridge
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import argparse
import cv2
import json
import logging
import numpy as np
import os
import os.path as osp
import pickle
import shutil


def _load_label_file(labels_path, label_folder, label_file):
  label_filepath = osp.join(labels_path, label_folder, label_file)

  try:  # open and read the labels
    with open(label_filepath, 'r') as f:
      labels = json.load(f)
  except Exception as ex:
    logging.warning(f'cannot open label file "{label_filepath}", due to {ex}')
    labels = None

  return labels

def _manage_temp_folder(action, folder_path):
  assert action in ['mkdir', 'rmdir'], 'action must be "mkdir" or "rmdir"'

  if action == 'mkdir':
    os.makedirs(folder_path, exist_ok=True)

  if action == 'rmdir':
    shutil.rmtree(folder_path)

def _prepare_calib_data(model, tmp_folder, recording, labels, image_ext,
                        src_res, tgt_res, face_resize, eyes_resize):
  # create a shortcut for already generated data
  npy_name = f'{osp.basename(recording)}.npy'
  npy_file = osp.join(tmp_folder, npy_name)
  if osp.exists(npy_file):
    logging.info(f'calibration data "{npy_name}" already exists, skipping ...')
    return

  # genetate calibration data by inference
  from runtime.facealign import FaceAlignment
  from runtime.transform import rescale_frame
  from runtime.inference import predict_model_output

  alignment = FaceAlignment(static_image_mode=False, min_detection_confidence=0.80)
  data_samples = [] # generated calibration data

  for label_id, label in enumerate(labels):
    for image_id, pred in zip(label['ids'], label['preds']):
      image_basename = f"{image_id} {'_'.join(pred + label['gts'])}" + image_ext
      image_path = osp.join(recording, image_basename)
      image = rescale_frame(cv2.imread(image_path), src_res, tgt_res)
      image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

      landmarks, theta = alignment.process(image)
      if len(landmarks) > 0:
        # Get face crop, eye crops and face landmarks
        hw_ratio = eyes_resize[1] / eyes_resize[0]
        crops, norm_ldmks, new_ldmks = alignment.get_face_crop(
          image, landmarks, theta, hw_ratio=hw_ratio,
        )
        # Inference: predict PoG in the camera coordinate system
        ort_outputs = predict_model_output(model, crops, norm_ldmks, face_resize, eyes_resize)
        data_sample = np.concatenate([
          ort_outputs[0][0],                              # extracted features
          ort_outputs[1][0],                              # predicted PoGs (in prediction space)
          np.array(label['gts'], dtype=np.float32),       # ground-truth (in camera coordinate space)
          np.array([label_id, theta], dtype=np.float32),  # additional information
        ])
        data_samples.append(data_sample)

  alignment.close()
  data_samples = np.stack(data_samples, axis=0)
  np.save(npy_file, data_samples)

def _weight_with_scheme(scheme, n_samples, **weight_kwargs):
  assert scheme in ['uni', 'ins', 'ens'], 'select weight scheme'

  kwargs = dict(
    ins_exp=1.0,
    ens_beta=0.9,
  )
  update_kwargs_by_pop(kwargs, weight_kwargs)

  if scheme == 'uni':
    weight = 1.0

  if scheme == 'ins':
    weight = 1.0 / (n_samples ** kwargs['ins_exp'])

  if scheme == 'ens':
    en_samples = (1.0 - kwargs['ens_beta'] ** n_samples) / (1.0 - kwargs['ens_beta'])
    weight = 1.0 / en_samples

  return weight

def _load_train_test_samples(folder_path, test_ratio=0.2, weight_scheme='ins', **weight_kwargs):
  calib_pt_cnt = lambda n: int(np.max(n[:, -2]) + 1)

  data_samples = [
    np.load(osp.join(folder_path, npy_file))
    for npy_file in os.listdir(folder_path)
    if npy_file.endswith('.npy')
  ]

  n_samples = sum([len(ds) for ds in data_samples])
  n_points = sum([calib_pt_cnt(ds) for ds in data_samples])

  # prescending steps should make sure that the number of samples
  # for each calibration point is sufficient (eg. more than 4)
  min_samples_pp = min([
    len(ds[ds[:, -2] == i])
    for ds in data_samples
    for i in range(calib_pt_cnt(ds))
  ])
  n_avg_test_samples_pp = int(n_samples * test_ratio / n_points)
  n_test_samples_pp = max(1, min(min_samples_pp - 1, n_avg_test_samples_pp))

  logging.info(f'{test_ratio} test ratio, {n_samples} samples, {n_points} calibration points')
  logging.info(f'randomly select {n_test_samples_pp} test samples per calibration point')

  train_samples, test_samples, train_weights = [], [], []
  for data_sample in data_samples:
    for i in range(calib_pt_cnt(data_sample)):
      samples = data_sample[data_sample[:, -2] == i]
      np.random.shuffle(samples)
      train_samples.append(samples[n_test_samples_pp:])
      test_samples.append(samples[:n_test_samples_pp])
      # apply a weight to alleviate inbalanced data
      weight = _weight_with_scheme(weight_scheme, len(samples), **weight_kwargs)
      train_weight = weight * np.ones(len(samples) - n_test_samples_pp)
      train_weights.append(train_weight)

  train_samples = np.concatenate(train_samples, axis=0)
  test_samples = np.concatenate(test_samples, axis=0)

  train_weights = np.concatenate(train_weights, axis=0)
  train_weights = train_weights / np.sum(train_weights)

  return train_samples, test_samples, train_weights

def _display_gaze_on_canvas(canvas, gaze_screen_xy, pv_mode, pv_items, **kwargs):
  if pv_mode == 'full' and 'gaze' in pv_items:
    gx, gy = gaze_screen_xy

    style_params = dict(radius=56, color=(0, 0, 255), thickness=4, lineType=cv2.LINE_AA)
    update_kwargs_by_pop(style_params, kwargs)

    cv2.circle(canvas, (gx, gy), **style_params)


def calibration(record_path, labels_path, model_path, out_folder,
                image_ext, method, **cfg_options):
  '''Calibrate the model with an extra model.'''

  from runtime.pipeline import load_onnx_model, rotate_vector_v

  kwargs = dict(
    src_res=(720, 1280),
    tgt_res=(480, 640),
    face_resize=(224, 224),
    eyes_resize=(224, 224),
    json_name='labels',
    tmp_folder='calib_temp',
    tmp_keep=False,
    model_name='calib',
    test_ratio=0.2,
    weight_scheme='ins',
    weight_kwargs=dict(),
    normalize_target=False,
    method_kwargs=dict(),
  )
  update_kwargs_by_pop(kwargs, cfg_options)

  # make temporary folder for calibration cache
  _manage_temp_folder('mkdir', kwargs['tmp_folder'])

  # load model and prepare calibration data
  model = load_onnx_model(model_path)
  label_folders = [
    folder_path
    for folder_path in os.listdir(labels_path)
    if osp.isdir(osp.join(labels_path, folder_path))
  ]
  for label_folder in label_folders:
    labels = _load_label_file(labels_path, label_folder, f'{kwargs["json_name"]}.json')
    if labels is None: continue
    recording = osp.join(record_path, label_folder)
    _prepare_calib_data(
      model, kwargs['tmp_folder'], recording, labels, image_ext,
      kwargs['src_res'], kwargs['tgt_res'],
      kwargs['face_resize'], kwargs['eyes_resize'],
    )

  # build calibration model by fitting a pipeline
  if method == 'huber':
    base_regressor = HuberRegressor(**kwargs['method_kwargs'])
    regressor = MultiOutputRegressor(base_regressor)
  if method == 'ridge':
    regressor = Ridge(**kwargs['method_kwargs'])
  if method == 'kernel-ridge':
    regressor = KernelRidge(**kwargs['method_kwargs'])

  pipeline = Pipeline(
    steps=[
      ('scalar', StandardScaler(with_mean=True, with_std=True)),
      ('regressor', regressor),
    ],
    verbose=True,
  )
  calib_model = TransformedTargetRegressor(
    regressor=pipeline,
    transformer=StandardScaler(with_mean=True, with_std=True),
  ) if kwargs['normalize_target'] else pipeline

  # perform calibration with the specified method
  train_samples, test_samples, train_weights = _load_train_test_samples(
    kwargs['tmp_folder'], kwargs['test_ratio'],
    kwargs['weight_scheme'], **kwargs['weight_kwargs'],
  )
  X_train, X_test = train_samples[:, :-6], test_samples[:, :-6]
  yt_train = rotate_vector_v(train_samples[:, -4], train_samples[:, -3], -train_samples[:, -1])
  yt_test = rotate_vector_v(test_samples[:, -4], test_samples[:, -3], -test_samples[:, -1])
  yp_test = test_samples[:, -6:-4]

  calib_model.fit(X_train, yt_train, regressor__sample_weight=train_weights)
  yt_pred = calib_model.predict(X_test)

  mean_err_a = np.mean(np.linalg.norm(yt_test - yt_pred, axis=1))
  logging.info(f'mean error (+) calibration: {mean_err_a} cm')
  mean_err_b = np.mean(np.linalg.norm(yt_test - yp_test, axis=1))
  logging.info(f'mean error (-) calibration: {mean_err_b} cm')

  # save calibrated model addon using pickle
  model_file = osp.join(out_folder, f'{kwargs["model_name"]}.pkl')
  with open(model_file, 'wb') as f:
    pickle.dump(calib_model, f)

  # remove temporary folder for calibration cache
  if not kwargs['tmp_keep']:
    _manage_temp_folder('rmdir', kwargs['tmp_folder'])

  return model, calib_model

def calibration_preview(model, calib_model, camera_id,
                        topleft_offset, screen_size_px, screen_size_cm,
                        capture_resolution, target_resolution,
                        face_resize=(224, 224), eyes_resize=(224, 224),
                        pv_mode='none', pv_window='preview',
                        pv_items=['frame', 'gaze', 'time', 'warn'],
                        gx_filt_params=dict(), gy_filt_params=dict()):
  from runtime.facealign import FaceAlignment
  from runtime.inference import gaze_vec_to_screen_xy, predict_model_output
  from runtime.transform import rescale_frame
  from runtime.pipeline import rotate_vector_a
  # from runtime.one_euro import OneEuroFilter
  from runtime.preview import (
    create_pv_canvas, display_canvas,
    display_warning_on_canvas,
  )

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

  # Initialize mediapipe pipeline for face mesh detection
  alignment = FaceAlignment(static_image_mode=False, min_detection_confidence=0.80)

  # [Warn] Normally, the camera will be opened correctly, check this on failure
  logging.info(f'camera id {camera_id}, camera is opened {capture.isOpened()}')

  while True:
    success, source_image = capture.read()
    if not success: continue

    image = rescale_frame(source_image, capture_resolution, target_resolution)
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    landmarks, theta = alignment.process(rgb_image)

    canvas = create_pv_canvas(image, background, pv_mode, pv_items)

    gaze_screen_xy = None # Reset before next prediction

    if len(landmarks) > 0:
      # Get face crop, eye crops and face landmarks
      hw_ratio = eyes_resize[1] / eyes_resize[0]
      crops, norm_ldmks, new_ldmks = alignment.get_face_crop(
        image, landmarks, theta, hw_ratio=hw_ratio,
      )
      # Inference: predict PoG in the camera coordinate system
      ort_outputs = predict_model_output(model, crops, norm_ldmks, face_resize, eyes_resize)
      features, gaze_xy = ort_outputs[0], ort_outputs[1]
      calib_gaze_xy = calib_model.predict(features)

      gaze_xy, calib_gaze_xy = gaze_xy[0], calib_gaze_xy[0]
      gaze_xy = rotate_vector_a(gaze_xy[0], gaze_xy[1], theta)
      calib_gaze_xy = rotate_vector_a(calib_gaze_xy[0], calib_gaze_xy[1], theta)

      gaze_screen_xy = gaze_vec_to_screen_xy(gaze_xy, topleft_offset,
                                             screen_size_px, screen_size_cm)
      calib_gaze_screen_xy = gaze_vec_to_screen_xy(calib_gaze_xy, topleft_offset,
                                                   screen_size_px, screen_size_cm)

      # Display extra information on the preview
      if gaze_screen_xy is not None:
        _display_gaze_on_canvas(
          canvas, gaze_screen_xy, pv_mode, pv_items,
          color=(0, 0, 255), radius=48,
        )
      if calib_gaze_screen_xy is not None:
        _display_gaze_on_canvas(
          canvas, calib_gaze_screen_xy, pv_mode, pv_items,
          color=(255, 0, 0), radius=36,
        )

    else:
      display_warning_on_canvas(canvas, pv_mode, pv_items)

    if display_canvas(pv_window, canvas, pv_mode, pv_items): break

  # Destroy named windows used for preview
  if pv_mode != 'none':
    cv2.destroyAllWindows()

  alignment.close()
  capture.release()


def main_procedure(cmdargs: argparse.Namespace):
  model_path = osp.abspath(cmdargs.model_path)
  record_path = osp.abspath(cmdargs.record_path)
  labels_path = osp.abspath(cmdargs.labels_path)

  # collect extra configurations
  cfg_options = {k:v for k, v in cmdargs.cfg_options} if cmdargs.cfg_options else {}

  try:  # make sure the output folder exists
    out_folder = osp.abspath(cmdargs.out_folder)
    os.makedirs(out_folder, exist_ok=True)
  except Exception as ex:
    logging.warning(f'cannot make output folder "{out_folder}", due to {ex}')

  # calibrate the model using extracted features
  resolve_estimator_runtime_path()
  model, calib_model = calibration(
    record_path, labels_path, model_path, out_folder,
    cmdargs.img_ext, cmdargs.method, **cfg_options,
  )

  # live preview calibration result
  if cmdargs.preview:
    from runtime.miscellaneous import load_toml_secure

    config = load_toml_secure(cmdargs.config)
    config.pop('checkpoint')  # not needed

    logging.info(f'live preview will start in a few seconds')
    calibration_preview(model, calib_model, **config)
    logging.info(f'live preview finished, now exiting')



if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Calibrate the model with an extra model.')

  parser.add_argument('--cfg-options', nargs='+', type=parse_key_value,
                      help='Extra configurations, e.g. --cfg-options "key=value".')

  parser.add_argument('--model-path', type=str, required=True, help='Model (with feats).')
  parser.add_argument('--method', type=str, default='huber',
                      choices=['huber', 'ridge', 'kernel-ridge'],
                      help='The method to use for calibration.')

  parser.add_argument('--record-path', type=str, help='The path to the stored recordings.')
  parser.add_argument('--labels-path', type=str, help='Root folder for the cleaned labels.')

  parser.add_argument('--img-ext', default='.jpg', type=parse_file_ext,
                      help='The extension of the image files.')
  parser.add_argument('--out-folder', type=str, default='output', help='Output folder.')

  parser.add_argument('--preview', action='store_true', default=False,
                      help='Preview the calibration result.')
  parser.add_argument('--config', type=str, default='estimator.toml',
                      help='Configuration for the main PoG estimator.')

  active_root_logger()
  main_procedure(parser.parse_args())
