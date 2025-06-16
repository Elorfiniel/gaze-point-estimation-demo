from runtime.es_config import EsConfig, EsConfigFns
from runtime.log import runtime_logger
from runtime.parallel import FunctionalTask, submit_functional_task

import concurrent.futures as futures
import os.path as osp


class BasePass:
  def before_pass(self):
    '''Hook: called before the pass starts processing any data.'''
    pass

  def after_pass(self):
    '''Hook: called after the pass finishes processing all data.'''
    pass

  def collect_data(self) -> list:
    '''Collect the data to be processed into a list.'''
    pass

  def process_data(self, data):
    '''Process the collected data.'''
    pass

  def run(self):
    '''Run the pass to process the collected data.'''

    self.before_pass()

    data_list = self.collect_data()
    for data in data_list:
      self.process_data(data)

    self.after_pass()


class RecordingPass(BasePass):

  PASSES = dict()

  @staticmethod
  def process(recording_path: str, an_config: EsConfig):
    RecordingPass(recording_path, an_config).run()

  def __init__(self, recording_path: str, an_config: EsConfig):
    self.recording_path = recording_path
    self.an_config = an_config

  def after_pass(self):
    rt_logger = runtime_logger(name='annotator').getChild('update')
    rt_logger.info(f'finished processing for recording "{self.recording_path}"')

  def collect_data(self):
    pass_config = EsConfigFns.named_dict(self.an_config, 'recording_pass')
    return (self.PASSES[p] for p in pass_config['passes'])

  def process_data(self, data: BasePass):
    data(self.recording_path, self.an_config).run()


class MainPass(BasePass):
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
        yield FunctionalTask(RecordingPass.process, *args)

    return task_generator()

  def process_data(self, data: FunctionalTask):
    rt_logger = runtime_logger(name='annotator').getChild('parallel')
    submit_functional_task(data, self.executor, rt_logger)
