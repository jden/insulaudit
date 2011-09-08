
from cli.log import LoggingApp
from utils import GlobalOptions
import utils

class Application(LoggingApp):
  """Test Hello World
  """
  name = "insulaudit"
  devices = { }

  def __init__(self):
    kwds = { 'root': True }
    super(Application, self).__init__(**kwds)
  
  def setup(self):
    # just after wrapping argument during __call__
    super(Application, self).setup( )
    #self.add_param("bar", help="fake option", action='store_true')
    utils.setup_global_options(self.argparser)
    self.commands = self.argparser.add_subparsers(dest='device',
                      description="app subcommand descr",
                      title="fake title",
                      help='fake help on this command')

    self.setup_commands( )

  def pre_run(self):
    # called just before main, updates params, parses args
    super(Application, self).pre_run()
    #pprint(self.__dict__)
    device        = self.devices[self.params.device]
    self.selected = device
    if callable(device.pre_run):
      device.pre_run(self)

  def setup_commands( ):
    pass

  def main(self):
    #pprint(self.params)
    self.selected.main(self)


#####
# EOF