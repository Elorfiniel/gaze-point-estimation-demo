from .base_pass import BasePass
from .miscellaneous import require_context, dump_json

from runtime.es_config import EsConfig

import os.path as osp


class LoadSamplesPass(BasePass):

  PASS_NAME = 'data_pass.load_samples'

  SAMPLE_TEMPLATE = dict()

  def __init__(self, recording_path: str, an_config: EsConfig):
    pass  # Use default template for all data samples

  def before_pass(self, context: dict, **kwargs):
    context['samples'] = dict()

  def collect_data(self, context: dict, **kwargs):
    return context['targets']

  def process_data(self, data, context: dict, **kwargs):
    image_names = [f'{fid:05d}.jpg' for fid in data['fids']]

    for image_name in image_names:
      context['samples'][image_name] = self.SAMPLE_TEMPLATE.copy()

  def run(self, context: dict, **kwargs):
    require_context(self, context, ['targets'])
    super().run(context=context, **kwargs)


class SaveSamplesPass(BasePass):

  PASS_NAME = 'data_pass.save_samples'

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path

  def run(self, context: dict, **kwargs):
    require_context(self, context, ['samples'])
    json_path = osp.join(self.recording_path, 'labels', 'samples.json')
    dump_json(json_path, context['samples'])
