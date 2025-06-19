from .base_pass import BasePass
from .data_pass import LoadSamplesPass, SaveSamplesPass
from .face_pass import FaceDetectPass, FaceEmbedPass, FaceVerifyPass
from .io_pass import LoadTargetsPass
from .mgmt_pass import ReorganizeFolderPass

from runtime.es_config import EsConfig, EsConfigFns
from runtime.log import runtime_logger
from runtime.parallel import FunctionalTask, submit_functional_task

import concurrent.futures as futures
import os.path as osp


IMPLEMENTED_PASSES = [
  LoadSamplesPass,
  SaveSamplesPass,
  FaceDetectPass,
  FaceEmbedPass,
  FaceVerifyPass,
  LoadTargetsPass,
  ReorganizeFolderPass,
  # Add other passes here as needed
]


class MainEntryPass(BasePass):

  PASS_NAME = 'main_pass.main_entry'

  PASSES = {P.PASS_NAME:P for P in IMPLEMENTED_PASSES}

  @staticmethod
  def process(recording_path: str, an_config: EsConfig):
    MainEntryPass(recording_path, an_config).run()

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path
    self.an_config = an_config

  def before_pass(self, **kwargs):
    self.rt_context = dict() # Context for intermediate results

  def after_pass(self, **kwargs):
    rt_logger = runtime_logger(name='annotator').getChild('messages')
    rt_logger.info(f'finished processing for recording "{self.recording_path}"')

  def collect_data(self, **kwargs):
    pass_config = EsConfigFns.named_dict(self.an_config, 'main_pass')
    return (self.PASSES[p] for p in pass_config['run_passes'])

  def process_data(self, data: BasePass, **kwargs):
    data(self.recording_path, self.an_config).run(context=self.rt_context)


class ParallelEntryPass(BasePass):

  PASS_NAME = 'main_pass.parallel_entry'

  def __init__(self, record_path: str, recordings: list, an_config: EsConfig):
    self.record_path = record_path
    self.recordings = recordings
    self.an_config = an_config

  def before_pass(self, **kwargs):
    pass_config = EsConfigFns.named_dict(self.an_config, 'main_pass')
    self.executor = futures.ProcessPoolExecutor(max_workers=pass_config['num_workers'])

  def after_pass(self, **kwargs):
    self.executor.shutdown(wait=True)

  def collect_data(self, **kwargs):
    def task_generator():
      for recording in self.recordings:
        args = (osp.join(self.record_path, recording), self.an_config)
        yield FunctionalTask(MainEntryPass.process, *args)

    return task_generator()

  def process_data(self, data: FunctionalTask, **kwargs):
    rt_logger = runtime_logger(name='annotator').getChild('parallel')
    submit_functional_task(data, self.executor, rt_logger)
