# Wrapper class for mediapipe face mesh solution
# A convinient helper class to do face alignment

# From: https://gitee.com/elorfiniel/gaze-point-estimation-2023/blob/master/source/utils/common/facealign.py
# Commit: 8797c10abcf35165cb2ffc0c6a46a72b684e7eb4
# Author: Elorfiniel (markgenthusiastic@gmail.com)

import mediapipe as mp
import numpy as np
import cv2 as cv2
import logging


# Commonly used landmarks detected by mediapipe face mesh
def _get_landmark_group_indices(connections):
  landmark_connections = []

  for connection in connections:
    landmark_connections.extend(connection)

  return list(set(landmark_connections))

_FACEMESH_CONTOURS = _get_landmark_group_indices(
  mp.solutions.face_mesh_connections.FACEMESH_CONTOURS)
_FACEMESH_FACE_OVAL = _get_landmark_group_indices(
  mp.solutions.face_mesh_connections.FACEMESH_FACE_OVAL)
_FACEMESH_IRISES = _get_landmark_group_indices(
  mp.solutions.face_mesh_connections.FACEMESH_IRISES)
_FACEMESH_LEFT_EYEBROW = _get_landmark_group_indices(
  mp.solutions.face_mesh_connections.FACEMESH_LEFT_EYEBROW)
_FACEMESH_RIGHT_EYEBROW = _get_landmark_group_indices(
  mp.solutions.face_mesh_connections.FACEMESH_RIGHT_EYEBROW)
_FACEMESH_LIPS = _get_landmark_group_indices(
  mp.solutions.face_mesh_connections.FACEMESH_LIPS)
_FACEMESH_TESSELATION = _get_landmark_group_indices(
  mp.solutions.face_mesh_connections.FACEMESH_TESSELATION)
_LEFT_IRIS = _get_landmark_group_indices(
  mp.solutions.face_mesh_connections.FACEMESH_LEFT_IRIS)
_RIGHT_IRIS = _get_landmark_group_indices(
  mp.solutions.face_mesh_connections.FACEMESH_RIGHT_IRIS)
_LEFT_EYE = _get_landmark_group_indices(
  mp.solutions.face_mesh_connections.FACEMESH_LEFT_EYE)
_RIGHT_EYE = _get_landmark_group_indices(
  mp.solutions.face_mesh_connections.FACEMESH_RIGHT_EYE)
_LEFT_EYE_CENTER = [473]
_RIGHT_EYE_CENTER = [468]


class NormalizedCropRegion():
  def __init__(self, crop: np.ndarray, sas: np.ndarray):
    self._crop = crop  # 3-channel (RGB) image crop
    self._sas = sas    # Screen coordinate: (x, y, w, h)

  def get_crop(self):
    return self._crop

  def get_sas(self):
    return self._sas

  def get_shift(self):
    return self._sas[:2]

  def get_size(self):
    return self._sas[3:]

class FaceAlignment():
  '''Wrapper class for mediapipe face mesh solution.'''

  def __init__(self,
               static_image_mode=True,
               max_num_faces=1,
               min_detection_confidence=0.6,
               min_tracking_confidence=0.6):
    '''Helper class for mediapipe face mesh solution with context management.

    Similar to mediapipe solutions, we recommand the use of `with` block:

    ```
    with FaceAlignment(min_detection_confidence=0.8) as alignment:
      image_path = generate_image_path(...)
      image = load_and_convert_to_rgb(image_path)
      landmarks, theta = alignment.process(image)
      if len(landmarks) == 0: continue
      crops, norm_ldmks, new_ldmks = alignment.get_face_crop(image, landmarks, theta)
    ```

    `static_image_mode`: treat the input as stand-alone images or frames from a video stream.

    `max_num_faces`: maximum number of faces to detect.

    `min_detection_confidence`: minimum confidence value (0.0, 1.0) for successful face detection.

    `min_tracking_confidence`: minimum confidence value (0.0, 1.0) for successful face landmarks tracking.
    '''

    self._static_image_mode = static_image_mode
    self._max_num_faces = max_num_faces
    self._min_detection_confidence = min_detection_confidence
    self._min_tracking_confidence = min_tracking_confidence

    # TODO: Add support for multiple faces in one image
    if max_num_faces != 1:
      logging.warning("currently, multiple faces are not supported")
      self._max_num_faces = 1

    self._face_mesh = mp.solutions.face_mesh.FaceMesh(
      static_image_mode=self._static_image_mode,
      max_num_faces=self._max_num_faces,
      refine_landmarks=True,
      min_detection_confidence=self._min_detection_confidence,
      min_tracking_confidence=self._min_tracking_confidence,
    )
    self._closed = False

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.close()

  def _parse_mediapipe_landmarks(self, landmarks):
    # TODO: Add interface for z coordinate
    return np.array([(ldmk.x, ldmk.y) for ldmk in landmarks], dtype=np.float32)

  def _denormalize_landmarks(self, image_h, image_w, landmarks: np.ndarray):
    return landmarks * np.array([image_w, image_h])

  def _l2_norm(self, array: np.ndarray, axis=None):
    return np.sqrt(np.sum(array**2, axis=axis))

  def _get_bbox_for_points(self, points):
    x_max, y_max = np.max(points, axis=0)
    x_min, y_min = np.min(points, axis=0)
    return float(x_min), float(y_min), float(x_max), float(y_max)

  def _get_rotation_angle(self, ldmk1, ldmk2):
    sin = (ldmk1[1] - ldmk2[1]) / self._l2_norm(ldmk1 - ldmk2)
    return -np.rad2deg(np.arcsin(sin))

  def _get_crop_shift_and_size(self, origin, bbox, metric):
    bbox_cx = (bbox[0] + bbox[2]) / 2
    bbox_cy = (bbox[1] + bbox[3]) / 2

    shift = np.array([bbox_cx, bbox_cy]) - np.array(origin)
    size = np.array([bbox[2] - bbox[0], bbox[3] - bbox[1]])

    return np.concatenate([shift, size]) / metric

  def get_rotation_matrix_2d(self, center=(0.0, 0.0), theta=0.0, scale=1.0):
    return cv2.getRotationMatrix2D(center, theta, scale)

  def apply_rotation_matrix_2d(self, M: np.ndarray, points: np.ndarray):
    P = np.concatenate([points, np.ones(shape=(len(points), 1))], axis=1)
    return np.transpose(np.dot(M, np.transpose(P)))

  def _rotate_with_bounds(self, image, angle):
    height, width, _ = image.shape
    # TODO: Consider the nubmer of padded pixels for better efficiency
    length = 2 * max(height, width)
    a = int((length - width) / 2)
    b = int((length - height) / 2)
    padded = cv2.copyMakeBorder(image, b, b, a, a, cv2.BORDER_CONSTANT, None, value=(0, 0, 0))
    M = self.get_rotation_matrix_2d((width/2 + a, height/2 + b), angle, scale=1.0)
    return cv2.warpAffine(padded, M, (width + 2*a, height + 2*b)), a, b, M

  def _get_eye_crop_bbox(self, eye_center, bbox, width_expand, hw_ratio):
    width = width_expand * (bbox[2] - bbox[0])
    height = width * hw_ratio

    x_min = eye_center[0] - width / 2
    x_max = eye_center[0] + width / 2
    y_min = eye_center[1] - height / 2
    y_max = eye_center[1] + height / 2

    return x_min, y_min, x_max, y_max

  def _get_eyes_crop(self, rotated, landmarks, cam_center, cam_metric,
                     width_expand=1.6, hw_ratio=0.6):
    '''Takes as input the cropped face and correspoinding landmarks,
    return the cropped regions for both eyes.
    '''

    # Get landmarks for both right eye and left eye
    reye_bbox = self._get_bbox_for_points(landmarks[_RIGHT_EYE])
    leye_bbox = self._get_bbox_for_points(landmarks[_LEFT_EYE])
    reye_center = landmarks[_RIGHT_EYE_CENTER[0]]
    leye_center = landmarks[_LEFT_EYE_CENTER[0]]

    # Get eye region bounds with the ratio of height over width
    rcrop_bbox = self._get_eye_crop_bbox(reye_center, reye_bbox, width_expand, hw_ratio)
    lcrop_bbox = self._get_eye_crop_bbox(leye_center, leye_bbox, width_expand, hw_ratio)
    rx_min, ry_min, rx_max, ry_max = np.asarray(rcrop_bbox, dtype=int)
    lx_min, ly_min, lx_max, ly_max = np.asarray(lcrop_bbox, dtype=int)

    reye_crop = NormalizedCropRegion(
      rotated[ry_min:ry_max, rx_min:rx_max],
      self._get_crop_shift_and_size(
        cam_center,
        [rx_min, ry_min, rx_max, ry_max],
        cam_metric,
        ),
    )
    leye_crop = NormalizedCropRegion(
      rotated[ly_min:ly_max, lx_min:lx_max],
      self._get_crop_shift_and_size(
        cam_center,
        [lx_min, ly_min, lx_max, ly_max],
        cam_metric,
      ),
    )

    return reye_crop, leye_crop

  def process(self, image: np.ndarray):
    '''Takes as input an RGB image of shape `(h, w, c)` and produces facial
    landmarks with mediapipe face mesh solution. Additionally, a rotation
    angle `theta` is returned, which the caller may use as a hint for alignment.

    Note that `uint8` is assumed as the data type for the input image.
    '''

    height, width, _ = image.shape

    # Mark the image as not writable to pass by reference
    image.flags.writeable = False
    results = self._face_mesh.process(image)
    image.flags.writeable = True

    if not results.multi_face_landmarks:
      return np.array([]), 0.0

    landmarks = results.multi_face_landmarks[0].landmark
    landmarks = self._parse_mediapipe_landmarks(landmarks)
    landmarks = self._denormalize_landmarks(height, width, landmarks)

    # Simply use inner eye cornors to align the face, explanation:
    #   pt_r = landmarks[133]   # Right inner eye cornor
    #   pt_l = landmarks[362]   # Left inner eye cornor
    #   sin = (pt_r[1] - pt_l[1]) / self._l2_norm(pt_r - pt_l)
    #   theta = -np.rad2deg(np.arcsin(sin))
    # TODO: Refine current method for better alignment
    theta = self._get_rotation_angle(landmarks[133], landmarks[362])

    return landmarks, theta

  def close(self):
    '''Wrapper method for `close()` method of `FaceMesh` object.'''
    if not self._closed:
      self._face_mesh.close()
      self._closed = True

  def get_face_crop_without_align(self, image, landmarks, with_eyes=True,
                                  width_expand=1.6, hw_ratio=0.6):
    '''Takes as input an RGB image of shape `(h, w, c)`, and results
    from `process()` method, generates a face crop, and eye
    regions for both eyes if `with_eyes` is True.

    `with_eyes`: whether to generate crops for both eyes.

    `width_expand`: expand the width between inner and outer eye corners,
    which is then used to crop eye regions.

    `hw_ratio`: the ratio of height and width for crop eye regions.
    '''

    height, width, _ = image.shape

    bbox_ldmks = self._get_bbox_for_points(landmarks)
    cx_min, cy_min, cx_max, cy_max = bbox_ldmks

    center_x = (cx_min + cx_max) / 2.0
    center_y = (cy_min + cy_max) / 2.0
    crop_half_a = 0.4 * (cx_max - cx_min)
    crop_half_b = 0.1 * (cy_max - cy_min)
    crop_half_w = crop_half_a + crop_half_b

    padded, a, b, M = self._rotate_with_bounds(image, 0.0)
    new_ldmks = landmarks + np.array([a, b])

    cx_min = int(center_x - crop_half_w + a)
    cx_max = int(center_x + crop_half_w + a)
    cy_min = int(center_y - crop_half_w + b)
    cy_max = int(center_y + crop_half_w + b)
    cy_max = cx_max - cx_min + cy_min

    camera_center = [padded.shape[1] / 2, padded.shape[0] / 2]
    camera_metric = max(height, width)

    face_crop = NormalizedCropRegion(
      padded[cy_min:cy_max, cx_min:cx_max],
      self._get_crop_shift_and_size(
        camera_center,
        [cx_min, cy_min, cx_max, cy_max],
        camera_metric,
      ),
    )

    reye_crop, leye_crop = None, None
    if with_eyes:
      reye_crop, leye_crop = self._get_eyes_crop(
        padded, new_ldmks,
        camera_center, camera_metric,
        width_expand, hw_ratio,
      )

    # Normalize landmarks using camera center and camera metric (used for training)
    norm_ldmks = (new_ldmks - np.array(camera_center)) / camera_metric

    # Remove landmark shift introduced by padding during image rotation (visualization)
    new_ldmks = new_ldmks - np.array([cx_min, cy_min])

    return (face_crop, reye_crop, leye_crop), norm_ldmks, new_ldmks

  def get_face_crop(self, image, landmarks, theta, with_eyes=True,
                    width_expand=1.6, hw_ratio=0.6):
    '''Takes as input an RGB image of shape `(h, w, c)`, and results
    from `process()` method, generates an aligned face crop, and eye
    regions for both eyes if `with_eyes` is True.

    `with_eyes`: whether to generate crops for both eyes.

    `width_expand`: expand the width between inner and outer eye corners,
    which is then used to crop eye regions.

    `hw_ratio`: the ratio of height and width for crop eye regions.
    '''

    height, width, _ = image.shape

    # Generate rotation matrix using `theta`, rotate around image center
    rotated, a, b, M = self._rotate_with_bounds(image, theta)
    new_ldmks = self.apply_rotation_matrix_2d(M, landmarks + np.array([a, b]))

    # The center of rotation is the center of the original image
    # Thus, a normalized position vector `CA = A - C` can be calculated
    camera_center = [rotated.shape[1] / 2, rotated.shape[0] / 2]
    camera_metric = max(height, width)

    # Crop face from the rotated image according to the bounding box
    # TODO: Implement better method for face cropping
    bbox_new_ldmks = self._get_bbox_for_points(new_ldmks)
    cx_min, cy_min, cx_max, cy_max = np.asarray(bbox_new_ldmks, dtype=int)
    # It can be observed that face width in the rotated image fits
    # well with face mesh approximation (cx_max - cx_min)
    cy_max = cx_max - cx_min + cy_min

    face_crop = NormalizedCropRegion(
      rotated[cy_min:cy_max, cx_min:cx_max],
      self._get_crop_shift_and_size(
        camera_center,
        [cx_min, cy_min, cx_max, cy_max],
        camera_metric,
      ),
    )

    # Crop eye regions from the rotated image, if cropping with eyes
    reye_crop, leye_crop = None, None
    if with_eyes:
      reye_crop, leye_crop = self._get_eyes_crop(
        rotated, new_ldmks,
        camera_center, camera_metric,
        width_expand, hw_ratio,
      )

    # Normalize landmarks using camera center and camera metric (used for training)
    norm_ldmks = (new_ldmks - np.array(camera_center)) / camera_metric

    # Remove landmark shift introduced by padding during image rotation
    new_ldmks = new_ldmks - np.array([cx_min, cy_min])

    return (face_crop, reye_crop, leye_crop), norm_ldmks, new_ldmks
