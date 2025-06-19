from .base_pass import BasePass
from .miscellaneous import require_context

from runtime.es_config import EsConfig, EsConfigFns

import numpy as np
import sklearn.neighbors as skn


class LocalOutlierPass(BasePass):

  PASS_NAME = 'out_pass.local_outlier'

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path
    self.pass_config = EsConfigFns.named_dict(an_config, 'out_pass')

  def collect_data(self, context: dict, **kwargs):
    return context['targets']

  def process_data(self, data, context: dict, **kwargs):
    image_names = [f'{fid:05d}.jpg' for fid in data['fids']]

    pseudos_xy = dict() # Image -> Pseudo PoG
    for image_name in image_names:
      sample_dict = context['samples'][image_name]
      if not sample_dict['face_mesh']: continue
      if self.pass_config['verify_main_face']:
        if not sample_dict['main_face']: continue
      pseudos_xy[image_name] = sample_dict['pseudo_xy']

    if len(pseudos_xy) >= self.pass_config['lof_min_samples']:
      pseudos = np.array([pseudos_xy[n] for n in pseudos_xy], dtype=np.float32)

      n_neighbors = max(int(self.pass_config['lof_p_neighbors'] * len(pseudos)), 1)
      lof = skn.LocalOutlierFactor(n_neighbors=n_neighbors, contamination='auto')
      inliers = lof.fit_predict(pseudos) == 1
      if inliers.sum() < self.pass_config['lof_min_samples']:
        inliers = np.zeros_like(inliers, dtype=bool)

    else:
      inliers = np.zeros(len(pseudos_xy), dtype=bool)

    inliers = {n:bool(i) for n, i in zip(pseudos_xy, inliers)}

    for image_name in image_names:
      context['samples'][image_name].update(
        inlier=inliers.get(image_name, False),
      )

  def run(self, context: dict, **kwargs):
    require_context(self, context, ['targets', 'samples'])
    super().run(context=context, **kwargs)
