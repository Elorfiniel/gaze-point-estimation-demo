from .base_pass import BasePass
from .miscellaneous import require_context, dump_json, format_number

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
import sklearn.cluster as skc


def adjusted_mesh(image: np.ndarray, image_mp: np.ndarray, landmarks: np.ndarray):
  '''Adjust face mesh to fit the original image, rather than the potentially rescaled one.'''

  src_h, src_w, _ = image.shape
  tgt_h, tgt_w, _ = image_mp.shape

  src_asp = src_w / src_h
  tgt_asp = tgt_w / tgt_h

  if tgt_asp > src_asp:
    rescale_h = int(src_w / tgt_asp)
    mesh = landmarks * rescale_h / tgt_h
    padding_h = (src_h - rescale_h) // 2
    mesh[:, 1] += padding_h
  if tgt_asp < src_asp:
    rescale_w = int(src_h * tgt_asp)
    mesh = landmarks * rescale_w / tgt_w
    padding_w = (src_w - rescale_w) // 2
    mesh[:, 0] += padding_w

  return mesh

def alignment_angle(landmarks: np.ndarray):
  '''Get alignment angle for face mesh.'''

  reye_icorner, leye_icorner = landmarks[133], landmarks[362]

  delta_y = reye_icorner[1] - leye_icorner[1]
  norm = np.linalg.norm(reye_icorner - leye_icorner)
  theta = -np.rad2deg(np.arcsin(delta_y / norm))

  return theta

def alignd_rotate(image: np.ndarray, landmarks: np.ndarray, theta: float):
  '''Rotate image and landmarks according to alignment angle theta.'''

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
  '''Get the bounding box for these landmarks.'''

  x_min, y_min = np.min(landmarks, axis=0)
  x_max, y_max = np.max(landmarks, axis=0)

  return x_min, y_min, x_max, y_max

def scaled_bbox(x_min, y_min, x_max, y_max, scale: float = 1.0):
  '''Scale bounding box by the given factor wrt box center.'''

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

def aligned_face(image: np.ndarray, landmarks: np.ndarray):
  '''Get aligned face patch of size 160x160 from the image for face recognition.'''

  theta = alignment_angle(landmarks)
  image_rot, ldmks_rot = alignd_rotate(image, landmarks, theta)

  x_min, y_min, x_max, y_max = bounding_box(ldmks_rot)
  y_max = y_min + x_max - x_min

  x_min, y_min, x_max, y_max = scaled_bbox(x_min, y_min, x_max, y_max, scale=2.0)
  face_patch = scaled_crop(image_rot, (x_min, y_min, x_max, y_max), (160, 160))

  return face_patch

def embeded_face(image: np.ndarray, model: onnxruntime.InferenceSession):
  '''Embed croped face image into 512-D vector, produced by FaceNet model.'''

  ort_ipt = np.transpose(image, (2, 0, 1)).astype(np.float32)
  ort_ipt = np.expand_dims((ort_ipt - 127.5) / 128.0, axis=0)
  ort_opt = np.squeeze(model.run(None, {'img': ort_ipt})[0])

  return ort_opt


class MpInferencer(Inferencer):

  EXPECTED_LDMK_INDICES = np.array([
    122, 193, 55, 65, 52, 53, 46, 124, 35, 31, 228, 229, 230, 231, 232, 128, 245,
    351, 417, 285, 295, 282, 283, 276, 353, 265, 261, 448, 449, 450, 451, 452, 357, 465,
  ], dtype=int)

  def run(self, model, align, image, to_rgb=True):
    '''Run inference with model on the aligned image.

    Returns a result dictionary with the following keys:
      success: bool, whether the inference was successful.
      pog_cam: non-filtered PoG (x, y) in camera coordinate frame.
      mesh: the detected face mesh (478 landmarks).
    '''

    result = dict(success=False, pog_cam=None, mesh=None)

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
      result.update(success=True, pog_cam=pog_cam, mesh=landmarks)

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

    self.model_config_path = EsConfigFns.get_config_path(an_config)
    self.checkpoint_cfg = EsConfigFns.named_dict(an_config, 'checkpoint')
    self.transforms_cfg = EsConfigFns.named_dict(an_config, 'transform')
    self.alignment_cfg = EsConfigFns.named_dict(an_config, 'alignment')
    self.inferencer_cfg = EsConfigFns.named_dict(an_config, 'inference')

  def before_pass(self, context: dict, **kwargs):
    self.model = load_model(self.model_config_path, **self.checkpoint_cfg)

    self.transforms = Transforms(**self.transforms_cfg)
    self.alignment = FaceAlignment(**self.alignment_cfg)
    self.inferencer = MpInferencer(**self.inferencer_cfg)

  def after_pass(self, context: dict, **kwargs):
    self.alignment.close()

  def collect_data(self, context: dict, **kwargs):
    return context['targets']

  def process_data(self, data, context: dict, **kwargs):
    image_names = [f'{fid:05d}.jpg' for fid in data['fids']]

    for image_name in image_names:
      image_path = osp.join(self.recording_path, 'images', image_name)
      image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
      image_mp = self.transforms.transform(image)
      result = self.inferencer.run(self.model, self.alignment, image_mp)

      if result['success']:
        mesh = adjusted_mesh(image, image_mp, result['mesh'])
        mesh_name = image_name.replace('.jpg', '.npy')
        mesh_path = osp.join(self.recording_path, 'meshes', mesh_name)
        np.save(mesh_path, np.round(mesh, decimals=4))

        pseudo_xy = format_number(result['pog_cam'])
        update_dict = dict(face_mesh=True, pseudo_xy=pseudo_xy)

      else:
        update_dict = dict(face_mesh=False, pseudo_xy=[])

      context['samples'][image_name].update(update_dict)

  def run(self, context: dict, **kwargs):
    require_context(self, context, ['targets', 'samples'])
    super().run(context=context, **kwargs)


class FaceEmbedPass(BasePass):

  PASS_NAME = 'face_pass.face_embed'

  EMBED_DTYPE = [('image_name', 'U32'), ('embed', 'f4', (512, ))]

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path

    self.model_config_path = EsConfigFns.get_config_path(an_config)

  def before_pass(self, context: dict, **kwargs):
    self.embeds_folder = osp.join(self.recording_path, 'embeds')
    os.makedirs(self.embeds_folder, exist_ok=True)

    self.faces_folder = osp.join(self.embeds_folder, 'faces')
    os.makedirs(self.faces_folder, exist_ok=True)

    facenet_path = osp.join('resources', 'facenet.onnx')
    self.facenet = load_model(self.model_config_path, facenet_path)

    self.embeds = dict()  # Image -> Embedding

  def after_pass(self, context: dict, **kwargs):
    embeds = np.array([(n, e) for n, e in self.embeds.items()], dtype=self.EMBED_DTYPE)

    embeds_path = osp.join(self.embeds_folder, 'embeds.npy')
    np.save(embeds_path, embeds)

  def collect_data(self, context: dict, **kwargs):
    return context['targets']

  def process_data(self, data, context: dict, **kwargs):
    image_names = [f'{fid:05d}.jpg' for fid in data['fids']]

    for image_name in image_names:
      sample_dict = context['samples'][image_name]
      if not sample_dict['face_mesh']: continue

      image_path = osp.join(self.recording_path, 'images', image_name)
      image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)

      mesh_name = image_name.replace('.jpg', '.npy')
      mesh_path = osp.join(self.recording_path, 'meshes', mesh_name)
      mesh = np.load(mesh_path)

      face = aligned_face(image, mesh)
      face_path = osp.join(self.faces_folder, image_name)
      cv2.imwrite(face_path, face)

      embed = embeded_face(face, self.facenet)
      self.embeds[image_name] = embed

  def run(self, context: dict, **kwargs):
    require_context(self, context, ['targets', 'samples'])
    super().run(context=context, **kwargs)


class FaceVerifyPass(BasePass):

  PASS_NAME = 'face_pass.face_verify'

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path
    self.pass_config = EsConfigFns.named_dict(an_config, 'face_pass')

  def before_pass(self, context: dict, **kwargs):
    embeds_path = osp.join(self.recording_path, 'embeds', 'embeds.npy')
    embeds = np.load(embeds_path)

    embeddings = np.stack(embeds['embed'], axis=0)
    cluster = skc.DBSCAN(
      metric=self.pass_config['verify_metric'],
      eps=self.pass_config['verify_eps'],
      min_samples=self.pass_config['verify_min_samples'],
    ).fit(embeddings)

    unique_ids, counts = np.unique(
      cluster.labels_[cluster.labels_ != -1],
      return_counts=True,
    )

    self.face_id = int(unique_ids[np.argmax(counts)])
    self.n2id = {n:int(i) for n, i in zip(embeds['image_name'], cluster.labels_)}

  def after_pass(self, context: dict, **kwargs):
    verify_path = osp.join(self.recording_path, 'embeds', 'verify.json')
    dump_json(verify_path, dict(main_face=self.face_id, all_faces=self.n2id))

  def collect_data(self, context: dict, **kwargs):
    return context['targets']

  def process_data(self, data, context: dict, **kwargs):
    image_names = [f'{fid:05d}.jpg' for fid in data['fids']]

    for image_name in image_names:
      image_face_id = self.n2id.get(image_name, -2)
      context['samples'][image_name].update(
        main_face=image_face_id == self.face_id,
      )

  def run(self, context: dict, **kwargs):
    require_context(self, context, ['targets', 'samples'])
    super().run(context=context, **kwargs)
