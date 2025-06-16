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
