from .base_pass import BasePass
from .miscellaneous import load_json

from runtime.es_config import EsConfig

import json
import os.path as osp


class LoadTargetsPass(BasePass):

  PASS_NAME = 'io_pass.load_targets'

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path

  def run(self, context: dict, **kwargs):
    json_path = osp.join(self.recording_path, 'labels', 'targets.json')
    context['targets'] = load_json(json_path)
