from .base_pass import BasePass

from runtime.es_config import EsConfig, EsConfigFns
from runtime.facealign import FaceAlignment
from runtime.inference import Inferencer
from runtime.pipeline import load_model
from runtime.transform import Transforms

import cv2
import numpy as np
import os
import os.path as osp
import onnxruntime


def requirex_context(bpass: BasePass, context: dict, item_names: list):
  for item_name in item_names:
    if context.get(item_name) is None:
      raise RuntimeError(f'{bpass.PASS_NAME} requires "{item_name}" in context')


def alignd_rotate(image: np.ndarray, landmarks: np.ndarray, theta: float):
  image_h, image_w, _ = image.shape

  image_l = 2 * max(image_h, image_w)
  image_a = int((image_l - image_w) / 2)
  image_b = int((image_l - image_h) / 2)

  image_pad = cv2.copyMakeBorder(
    image, image_b, image_b, image_a, image_a,
    cv2.BORDER_CONSTANT, None, value=(0, 0, 0),
  )
  M = cv2.getRotationMatrix2D(
    center=(image_w / 2 + image_a, image_h / 2 + image_b),
    angle=theta, scale=1.0,
  )
  image_rot = cv2.warpAffine(
    image_pad, M, (image_w + 2 * image_a, image_h + 2 * image_b),
    flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT,
  )
  ldmks_rot = np.dot(
    np.concatenate([
      landmarks + np.array([image_a, image_b]),
      np.ones(shape=(len(landmarks), 1)),
    ], axis=1),
    M.T,
  )

  return image_rot, ldmks_rot

def bounding_box(landmarks: np.ndarray):
  x_min, y_min = np.min(landmarks, axis=0)
  x_max, y_max = np.max(landmarks, axis=0)
  return x_min, y_min, x_max, y_max

def scaled_bbox(x_min, y_min, x_max, y_max, scale: float = 1.0):
  x_mid = (x_min + x_max) / 2.0
  y_mid = (y_min + y_max) / 2.0

  w = (x_max - x_min) * scale
  h = (y_max - y_min) * scale

  x_min = x_mid - 0.5 * w
  x_max = x_mid + 0.5 * w
  y_min = y_mid - 0.5 * h
  y_max = y_mid + 0.5 * h

  return x_min, y_min, x_max, y_max

def scaled_crop(image: np.ndarray, bbox: tuple, size: tuple):
  '''Crop image region from the bounding box, then resize to the given size.

  Args:
    `image`: input image of shape `(h, w, c)`.
    `bbox`: region `(x_min, y_min, x_max, y_max)` to be cropped.
    `size`: size `(w, h)` of the output image.
  '''

  x_min, y_min, x_max, y_max = bbox
  crop_w, crop_h = size

  src_pts = np.array([(x_min, y_min), (x_max, y_min), (x_min, y_max)], dtype=np.float32)
  tgt_pts = np.array([(0, 0), (crop_w, 0), (0, crop_h)], dtype=np.float32)

  M = cv2.getAffineTransform(src_pts, tgt_pts)

  return cv2.warpAffine(image, M, (crop_w, crop_h), flags=cv2.INTER_CUBIC)

def aligned_face(image: np.ndarray, landmarks: np.ndarray, theta: float):
  '''Get aligned face patch of size 160x160 from the image for face recognition.'''

  image_rot, ldmks_rot = alignd_rotate(image, landmarks, theta)

  x_min, y_min, x_max, y_max = bounding_box(ldmks_rot)
  y_max = y_min + x_max - x_min

  x_min, y_min, x_max, y_max = scaled_bbox(x_min, y_min, x_max, y_max, scale=2.0)
  face_patch = scaled_crop(image_rot, (x_min, y_min, x_max, y_max), (160, 160))

  return face_patch

def embeded_face(image: np.ndarray, model: onnxruntime.InferenceSession):
  ort_ipt = np.transpose(image, (2, 0, 1)).astype(np.float32)
  ort_ipt = np.expand_dims((ort_ipt - 127.5) / 128.0, axis=0)
  ort_opt = np.squeeze(model.run(None, {'img': ort_ipt})[0])
  return ort_opt


class MediaPipeInferencer(Inferencer):

  EXPECTED_LDMK_INDICES = np.array([
    122, 193, 55, 65, 52, 53, 46, 124, 35, 31, 228, 229, 230, 231, 232, 128, 245,
    351, 417, 285, 295, 282, 283, 276, 353, 265, 261, 448, 449, 450, 451, 452, 357, 465,
  ], dtype=int)

  def run(self, model, align, image, to_rgb=True):
    '''Run inference with model on the aligned image.

    Returns a result dictionary with the following keys:
      success: bool, whether the inference was successful.
      pog_cam: non-filtered PoG (x, y) in camera coordinate frame.
      ldmks: detected landmarks in the image.
    '''

    result = dict(success=False, pog_cam=None, align_data=None)

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
      result.update(dict(
        success=True, pog_cam=pog_cam.tolist(),
        align_data=dict(landmarks=landmarks, theta=theta),
      ))

    return result

  def _validate(self, image, ldmks: np.ndarray):
    return len(ldmks) > 0 and self._ensure_face(image, ldmks)

  def _ensure_face(self, image, ldmks: np.ndarray):
    expected_ldmks = ldmks[self.EXPECTED_LDMK_INDICES]

    h, w, _ = image.shape

    v1 = np.logical_and(expected_ldmks[:, 0] >= 0, expected_ldmks[:, 0] <= w)
    v2 = np.logical_and(expected_ldmks[:, 1] >= 0, expected_ldmks[:, 1] <= h)

    return np.all(v1 & v2)


class FaceDetectPass(BasePass):

  PASS_NAME = 'face_pass.face_detect'

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path
    self.an_config = an_config

  def before_pass(self, context: dict, **kwargs):
    pass_config = EsConfigFns.named_dict(self.an_config, 'face_pass')

    if pass_config['run_facenet']:
      self.facenet_folder = osp.join(self.recording_path, 'facenet')
      context['facenet_folder'] = self.facenet_folder
      os.makedirs(self.facenet_folder, exist_ok=True)

    config_path = EsConfigFns.get_config_path(self.an_config)
    self.model = load_model(config_path, **EsConfigFns.named_dict(self.an_config, 'checkpoint'))

    self.transforms = Transforms(**EsConfigFns.named_dict(self.an_config, 'transform'))
    self.alignment = FaceAlignment(**EsConfigFns.named_dict(self.an_config, 'alignment'))
    self.inferencer = MediaPipeInferencer(**EsConfigFns.named_dict(self.an_config, 'inference'))

  def after_pass(self, context: dict, **kwargs):
    self.alignment.close()

  def collect_data(self, context: dict, **kwargs):
    return context['labels']

  def process_data(self, data, context: dict, **kwargs):
    pass_config = EsConfigFns.named_dict(self.an_config, 'face_pass')

    image_names = [f'{fid:05d}.jpg' for fid in data['fids']]

    results = []  # Inference results for each image
    for image_name in image_names:
      image_path = osp.join(self.recording_path, image_name)
      image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
      image = self.transforms.transform(image)
      result = self.inferencer.run(self.model, self.alignment, image)

      align_data = result.pop('align_data')
      if pass_config['run_facenet'] and result['success']:
        patch = aligned_face(image, **align_data)
        patch_path = osp.join(self.facenet_folder, image_name)
        cv2.imwrite(patch_path, patch)

      results.append(result)

    data['face'] = [r['success'] for r in results]
    data['pogs'] = [r['pog_cam'] for r in results]

  def run(self, context: dict, **kwargs):
    requirex_context(self, context, ['labels'])
    super().run(context=context, **kwargs)


class FaceEmbeddingPass(BasePass):

  PASS_NAME = 'face_pass.embedding'

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path
    self.an_config = an_config

  def before_pass(self, context: dict, **kwargs):
    self.facenet_folder = context['facenet_folder']
    context['face_embedding'] = dict()

    config_path = EsConfigFns.get_config_path(self.an_config)
    model_path = osp.join('resources', 'facenet.onnx')
    self.model = load_model(config_path, model_path)

  def collect_data(self, context: dict, **kwargs):
    image_names = os.listdir(self.facenet_folder)
    image_names.sort(reverse=False)
    return image_names

  def process_data(self, data, context: dict, **kwargs):
    image_path = osp.join(self.facenet_folder, data)
    image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    embed = embeded_face(image, self.model)
    context['face_embedding'][data] = embed

  def run(self, context: dict, **kwargs):
    requirex_context(self, context, ['facenet_folder'])
    super().run(context=context, **kwargs)
