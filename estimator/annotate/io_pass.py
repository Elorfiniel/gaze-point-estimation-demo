from .base_pass import BasePass

from runtime.es_config import EsConfig, EsConfigFns
from runtime.miscellaneous import deep_update

import json
import os.path as osp


class LoadContextPass(BasePass):

  PASS_NAME = 'io_pass.load_context'

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.an_config = an_config

  def run(self, context: dict, **kwargs):
    pass_config = EsConfigFns.named_dict(self.an_config, 'io_pass')
    deep_update(context, pass_config['context'], inplace=True)


class LoadTargetsPass(BasePass):

  PASS_NAME = 'io_pass.load_targets'

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path

  def run(self, context: dict, **kwargs):
    json_path = osp.join(self.recording_path, 'labels', 'targets.json')
    with open(json_path, 'r') as json_file:
      targets = json.load(json_file)
    context['targets'] = targets
