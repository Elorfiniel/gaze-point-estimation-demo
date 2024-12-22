from label.labels import LabelLoop, LabelPass
from label.parallel import run_parallel
from label.preview import *

from runtime.es_config import EsConfig, EsConfigFns
from runtime.facealign import FaceAlignment
from runtime.inference import Inferencer
from runtime.pipeline import load_model
from runtime.transform import Transforms

import argparse
import cv2
import concurrent.futures as futures
import logging
import numpy as np
import os
import os.path as osp
import sklearn.neighbors as skn


class LabelInferencer(Inferencer):

  EXPECTED_LDMK_INDICES = np.array([
    122, 193, 55, 65, 52, 53, 46, 124, 35, 31, 228, 229, 230, 231, 232, 128, 245,
    351, 417, 285, 295, 282, 283, 276, 353, 265, 261, 448, 449, 450, 451, 452, 357, 465,
  ], dtype=int)

  def run(self, model, align, image, to_rgb=True):
    '''Run inference with model on the aligned image.

    Returns a result dictionary with the following keys:
      success: bool, whether the inference was successful.
      pog_cam: non-filtered PoG (x, y) in camera coordinate frame.
    '''

    result = dict(success=False, pog_cam=None)

    if to_rgb: image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    landmarks, theta = align.process(image)
    if self._validate(image, landmarks):
      crops, norm_ldmks, _ = align.get_face_crop(
        image, landmarks, theta, hw_ratio=self.hw_ratio,
      )
      pog_scn, pog_cam = self.predict_fn(
        model, crops, norm_ldmks, theta,
        gx_filter=self.gx_filter, gy_filter=self.gy_filter,
      )
      result.update(dict(success=True, pog_cam=pog_cam.tolist()))

    return result

  def _validate(self, image, ldmks: np.ndarray):
    return len(ldmks) > 0 and self._ensure_face(image, ldmks)

  def _ensure_face(self, image, ldmks: np.ndarray):
    expected_ldmks = ldmks[self.EXPECTED_LDMK_INDICES]

    h, w, _ = image.shape

    v1 = np.logical_and(expected_ldmks[:, 0] >= 0, expected_ldmks[:, 0] <= w)
    v2 = np.logical_and(expected_ldmks[:, 1] >= 0, expected_ldmks[:, 1] <= h)

    return np.all(v1 & v2)


class PseudoLabelPass(LabelPass):
  def __init__(self, record_path, recording, config: EsConfig):
    self.folder = osp.join(record_path, recording)

    config_path = EsConfigFns.get_config_path(config)
    self.model = load_model(config_path, **EsConfigFns.named_dict(config, 'checkpoint'))

    self.transforms = Transforms(**EsConfigFns.named_dict(config, 'transform'))
    self.alignment = FaceAlignment(**EsConfigFns.named_dict(config, 'alignment'))
    self.inferencer = LabelInferencer(**EsConfigFns.named_dict(config, 'inference'))

  def _image_names(self, target, image_ext='.jpg'):
    return [f'{fid:05d}{image_ext}' for fid in target['fids']]

  def action(self, target):
    image_names = self._image_names(target)
    results = []  # Collected pseudo-labels

    for image_name in image_names:
      image_path = osp.join(self.folder, image_name)
      image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
      image = self.transforms.transform(image)
      result = self.inferencer.run(self.model, self.alignment, image)
      results.append(result)

    target['face'] = [r['success'] for r in results]
    target['pogs'] = [r['pog_cam'] for r in results]

class OutlierPass(LabelPass):
  def __init__(self, record_path, recording, config: EsConfig):
    pass_config = EsConfigFns.named_dict(config, 'outlier')
    self.min_samples = pass_config['min_samples']
    self.nn_ratio = pass_config['nn_ratio']

  def action(self, target):
    face_masks = np.array(target['face'], dtype=bool)

    if face_masks.sum() >= self.min_samples:
      face_pogs = [pog for pog in target['pogs'] if pog is not None]
      face_pogs = np.array(face_pogs, dtype=np.float32)

      lof = skn.LocalOutlierFactor(
        n_neighbors=max(int(self.nn_ratio * len(face_pogs)), 1),
        contamination='auto',
      )
      lof_masks = lof.fit_predict(face_pogs) == 1
      if lof_masks.sum() < self.min_samples:
        lof_masks = np.zeros_like(lof_masks, dtype=bool)

      masks = face_masks.copy()
      masks[face_masks] = lof_masks
    else:
      masks = np.zeros_like(face_masks, dtype=bool)

    target['okay'] = masks.tolist()

class VisualizePass(LabelPass):
  def __init__(self, record_path, recording, config: EsConfig):
    self.folder = osp.join(record_path, recording)
    self.config = EsConfigFns.named_dict(config, 'visualize')

  def _image_names(self, target, image_ext='.jpg'):
    return [f'{fid:05d}{image_ext}' for fid in target['fids']]

  def action(self, target):
    pseudo_list = [p for p in target['pogs'] if p is not None]
    image_paths = [
      osp.join(self.folder, image_name)
      for image_name in self._image_names(target)
    ]

    for image_path, pog, okay in zip(image_paths, target['pogs'], target['okay']):
      self.params_list.append(dict(
        image_path=image_path,
        target=[target['lx'], target['ly']], pseudo=pog,
        okay=okay, pseudo_list=pseudo_list,
      ))

  def before_target_iter(self):
    fig, ax_image, ax_label = create_preview_plots(self.config)
    self.plots = dict(fig=fig, ax_image=ax_image, ax_label=ax_label)
    self.params_list = [] # Parameters for each target

  def after_target_iter(self):
    anim_path = osp.join(self.folder, 'labels.mp4')
    function_animation(
      params_list=self.params_list, **self.plots,
    ).save(anim_path, writer='ffmpeg')
    close_preview_plots(self.plots['fig'])



def labeling_task(record_path, recording, config: EsConfig):
  label_actions = []  # Sequential actions to perform

  label_passes = [PseudoLabelPass, OutlierPass, VisualizePass]
  for label_pass in label_passes:
    label_actions.append(label_pass(record_path, recording, config))

  label_loop = LabelLoop(record_path, recording)
  for label_action in label_actions:
    label_loop.process(label_action)

def collect_recordings(cmdargs: argparse.Namespace):
  # Collect all recordings under the given path
  if cmdargs.record_path:
    record_path = osp.abspath(cmdargs.record_path)
    recordings = [
      item
      for item in os.listdir(record_path)
      if osp.isdir(osp.join(record_path, item))
    ]
  if cmdargs.recording:
    record_path = osp.dirname(osp.abspath(cmdargs.recording))
    recordings = [osp.basename(osp.abspath(cmdargs.recording))]

  if recordings:
    recordings.sort(reverse=False)

  logging.info(f'collected {len(recordings)} recordings from "{record_path}"')

  return record_path, recordings



def configure_logging(level=logging.INFO, force=False):
  logging.basicConfig(
    level=level, force=force,
    format='[ %(asctime)s ] process %(process)d - %(levelname)s: %(message)s',
    datefmt='%m-%d %H:%M:%S',
  )

def main_procedure(cmdargs: argparse.Namespace):
  config_path = osp.abspath(cmdargs.config)
  config = EsConfig.from_toml(config_path)
  EsConfigFns.set_config_path(config, config_path)

  record_path, recordings = collect_recordings(cmdargs)

  def task_generator():
    for recording in recordings:
      args = (record_path, recording, config)
      yield labeling_task, args

  executor = futures.ProcessPoolExecutor(cmdargs.max_workers)
  run_parallel(executor, task_generator())



if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Label the collected recordings.')

  parser.add_argument('--config', type=str, default='labeling.toml',
                      help='Configuration for the labeling process.')
  parser.add_argument('--max-workers', default=None, help='Maximum number of processes.')

  targets = parser.add_mutually_exclusive_group(required=True)
  targets.add_argument('--record-path', type=str, help='The path to the stored recordings.')
  targets.add_argument('--recording', type=str, help='The path to a specific recording.')

  configure_logging(logging.WARN, force=True)
  main_procedure(parser.parse_args())
