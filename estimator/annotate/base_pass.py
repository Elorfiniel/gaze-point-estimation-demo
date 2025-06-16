class BasePass:

  PASS_NAME = 'base_pass'

  def before_pass(self, **kwargs):
    '''Hook: called before the pass starts processing any data.'''
    pass

  def after_pass(self, **kwargs):
    '''Hook: called after the pass finishes processing all data.'''
    pass

  def collect_data(self, **kwargs) -> list:
    '''Collect the data to be processed into a list.'''
    pass

  def process_data(self, data, **kwargs):
    '''Process the collected data.'''
    pass

  def run(self, **kwargs):
    '''Run the pass to process the collected data.'''

    self.before_pass(**kwargs)

    data_list = self.collect_data(**kwargs)
    for data in data_list:
      self.process_data(data, **kwargs)

    self.after_pass(**kwargs)
