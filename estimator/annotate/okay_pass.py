from .base_pass import BasePass
from .miscellaneous import require_context

from runtime.es_config import EsConfig, EsConfigFns

import numpy as np
import sklearn.neighbors as skn


class LocalOutlierPass(BasePass):

  PASS_NAME = 'okay_pass.local_outlier'

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path
    self.an_config = an_config

  def collect_data(self, context: dict, **kwargs):
    return context['labels']

  def process_data(self, data, context: dict, **kwargs):
    pass_config = EsConfigFns.named_dict(self.an_config, 'okay_pass')

    face_masks = np.array(data['face'], dtype=bool)

    if face_masks.sum() >= pass_config['min_samples']:
      pseudos = [p for p in data['pogs'] if p is not None]
      pseudos = np.array(pseudos, dtype=np.float32)

      lof = skn.LocalOutlierFactor(
        n_neighbors=max(int(pass_config['p_neighbors'] * len(pseudos)), 1),
        contamination='auto',
      )
      lof_masks = lof.fit_predict(pseudos) == 1
      if lof_masks.sum() < pass_config['min_samples']:
        lof_masks = np.zeros_like(lof_masks, dtype=bool)

      okay_masks = face_masks.copy()
      okay_masks[face_masks] = lof_masks
    else:
      okay_masks = np.zeros_like(face_masks, dtype=bool)

    data['okay'] = okay_masks.tolist()

  def run(self, context: dict, **kwargs):
    require_context(self, context, ['labels'])
    super().run(context=context, **kwargs)
