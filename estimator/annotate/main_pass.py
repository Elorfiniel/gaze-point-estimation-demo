from .base_pass import BasePass

from runtime.es_config import EsConfig, EsConfigFns
from runtime.log import runtime_logger
from runtime.parallel import FunctionalTask, submit_functional_task

import concurrent.futures as futures
import os.path as osp


class MainEntryPass(BasePass):

  PASSES = dict()

  @staticmethod
  def process(recording_path: str, an_config: EsConfig):
    MainEntryPass(recording_path, an_config).run()

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path
    self.an_config = an_config

  def after_pass(self):
    rt_logger = runtime_logger(name='annotator').getChild('messages')
    rt_logger.info(f'finished processing for recording "{self.recording_path}"')

  def collect_data(self):
    pass_config = EsConfigFns.named_dict(self.an_config, 'main_pass')
    return (self.PASSES[p] for p in pass_config['passes'])

  def process_data(self, data: BasePass):
    data(self.recording_path, self.an_config).run()


class ParallelEntryPass(BasePass):
  def __init__(self, record_path: str, recordings: list, an_config: EsConfig):
    self.record_path = record_path
    self.recordings = recordings
    self.an_config = an_config

  def before_pass(self):
    pass_config = EsConfigFns.named_dict(self.an_config, 'main_pass')
    self.executor = futures.ProcessPoolExecutor(max_workers=pass_config['num_workers'])

  def after_pass(self):
    self.executor.shutdown(wait=True)

  def collect_data(self):
    def task_generator():
      for recording in self.recordings:
        args = (osp.join(self.record_path, recording), self.an_config)
        yield FunctionalTask(MainEntryPass.process, *args)

    return task_generator()

  def process_data(self, data: FunctionalTask):
    rt_logger = runtime_logger(name='annotator').getChild('parallel')
    submit_functional_task(data, self.executor, rt_logger)
