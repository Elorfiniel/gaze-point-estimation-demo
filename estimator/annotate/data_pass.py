from .base_pass import BasePass
from .miscellaneous import require_context, dump_json, load_json, format_number

from runtime.es_config import EsConfig, EsConfigFns

import os.path as osp


class LoadSamplesPass(BasePass):

  PASS_NAME = 'data_pass.load_samples'

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path
    self.pass_config = EsConfigFns.named_dict(an_config, 'data_pass')

  def before_pass(self, context: dict, **kwargs):
    context['samples'] = dict()

  def after_pass(self, context: dict, **kwargs):
    json_path = osp.join(self.recording_path, 'labels', 'samples.json')
    if not self.pass_config['refresh_samples'] and osp.exists(json_path):
      context['samples'] = load_json(json_path)

  def collect_data(self, context: dict, **kwargs):
    return context['targets']

  def process_data(self, data, context: dict, **kwargs):
    image_names = [f'{fid:05d}.jpg' for fid in data['fids']]
    target_xy = format_number([data['lx'], data['ly']])

    for image_name in image_names:
      context['samples'][image_name] = dict(
        target_id=data['tid'],
        target_xy=target_xy,
      )

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
