"""
Agent documentation goes here.
"""

__docformat__ = 'reStructuredText'

import logging
import sys
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC
sys.path.append("/home/sanka/NIRE_EMS/volttron/LoadPriorityControl/LPCv1/")
from Model.SmartPlug import SmartPlug
from Model.IoTDeviceGroup import IoTDeviceGroup
from Controller.GLEAMMMonitor import GLEAMMMonitor
from Controller.EMSControl import EMSControl
from Model.IoTDeviceGroupManager import IoTDeviceGroupManager
from Model.SmartPlugDataService  import SmartPlugDataService
from Model.GroupRepository import GroupRepository
from Controller.LoadPriorityControlEV import LoadPriorityControlEV
_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"


def facadeIoNMAgent(config_path, **kwargs):
    """
    Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.
    :type config_path: str
    :returns: Facadeionmagent
    :rtype: Facadeionmagent
    """
    try:
        config = utils.load_config(config_path)
    except Exception:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    setting1 = int(config.get('setting1', 1))
    setting2 = config.get('setting2', "some/random/topic")

    return Facadeionmagent(setting1, setting2, **kwargs)


class Facadeionmagent(Agent):
    """
    Document agent constructor here.
    """

    def __init__(self, setting1=1, setting2="some/random/topic", **kwargs):
        super(Facadeionmagent, self).__init__(**kwargs)
        _log.debug("vip_identity: " + self.core.identity)
        self.config_name = "GLEAMMAssets"  # Configuration name used in vctl config store command
        
        

        self.setting1 = setting1
        self.setting2 = setting2

        self.default_config = {"setting1": setting1,
                               "setting2": setting2}

        # Set a default configuration to ensure that self.configure is called immediately to setup
        # the agent.
        self.vip.config.set_default("config", self.default_config)
        self.core.periodic(20,self.dowork)
        # Hook self.configure up to changes to the configuration file "config".
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")
        

        
    def retrieve_configuration(self):
        """
        Retrieve the CSV configuration from the configuration store.
        """
        # Get the configuration data directly as a Python list of dictionaries
        csv_data = self.vip.config.get(self.config_name)
        if csv_data:
           # print(f"Retrieved CSV configuration data: {utils.jsonapi.dumps(csv_data, indent=2)}")
           pass
        else:
            print(f"No configuration found with the name '{self.config_name}'.")
        return csv_data

    def configure(self, config_name, action, contents):
        """
        Called after the Agent has connected to the message bus. If a configuration exists at startup
        this will be called before onstart.

        Is called every time the configuration in the store changes.
        """
        config = self.default_config.copy()
        config.update(contents)

        _log.debug("Configuring Agent")

        try:
            setting1 = int(config["setting1"])
            setting2 = config["setting2"]
        except ValueError as e:
            _log.error("ERROR PROCESSING CONFIGURATION: {}".format(e))
            return

        self.setting1 = setting1
        self.setting2 = setting2

        for x in self.setting2:
            self._create_subscriptions(str(x))
            print(str(x))

    def _create_subscriptions(self, topic):
        """
        Unsubscribe from all pub/sub topics and create a subscription to a topic in the configuration which triggers
        the _handle_publish callback
        """
        self.vip.pubsub.unsubscribe("pubsub", None, None)

        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=topic,
                                  callback=self._handle_publish)

    def _handle_publish(self, peer, sender, bus, topic, headers, message):
        """
        Callback triggered by the subscription setup using the topic from the agent's config file
        """
        self._GLEAMMmonitor.process_Message({'topic':topic, 'message':message})
    def dowork(self):
        #self._emscontroller.execute_Strategy()     
        self._groupManager.control_All_Groups()
    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        """
        This is method is called once the Agent has successfully connected to the platform.
        This is a good place to setup subscriptions if they are not dynamic or
        do any other startup activities that require a connection to the message bus.
        Called after any configurations methods that are called at startup.

        Usually not needed if using the configuration store.
        """
        # Example publish to pubsub
        self.vip.pubsub.publish('pubsub', "some/random/topic", message="HI!")
        self._devicelist=self.retrieve_configuration()
        self._groupManager = IoTDeviceGroupManager()
        self._group = IoTDeviceGroup() # Group Facade
        self._GLEAMMmonitor = GLEAMMMonitor() # Monitor for smart plug update
        #self._emscontroller = EMSControl()        
        self._gleamm_assets={}
       # self._emscontroller.set_Controller(LoadPriorityControlEV(),('lpc',3000))
       # self._emscontroller.set_Group(self._group)
        
        for item in self._devicelist:
            asset=SmartPlug(item['Device'],self.vip)
            asset._deviceType='gleammrload'
            asset._max_power_rating=int(item['Maxpower'])
            asset._power_multiply_factor=float(item['Mulitplyfactor'])
            asset._priority =int(item['Priority'])
            self._group.add_Device(asset)
            self._GLEAMMmonitor.register_Observer(asset)
            self._gleamm_assets[item['Device']]=asset
        self._groupManager.add_Group( self._group)
        self._groupManager.group_By_Priority()
        self._GLEAMMmonitor.set_EMS_Controller(self._groupManager)
        self._groupManager.control_All_Groups_set_cmd(('lpc',77000))  
        
        # Example RPC call
        # self.vip.rpc.call("some_agent", "some_method", arg1, arg2)

    @Core.receiver("onstop")
    def onstop(self, sender, **kwargs):
        """
        This method is called when the Agent is about to shutdown, but before it disconnects from
        the message bus.
        """
        pass

    @RPC.export
    def rpc_method(self, arg1, arg2, kwarg1=None, kwarg2=None):
        """
        RPC method

        May be called from another agent via self.core.rpc.call
        """
        return self.setting1 + arg1 - arg2

    @RPC.export
    def get_Facades_Consumption(self,sender)->dict:
        return self._groupManager.get_groups_consumption()
    
    @RPC.export
    def execute_Control_all_Groups(self,cmd:dict,sender)->None:
        self._group_mode_selector=0  
        self._groupManager.control_All_Groups_set_cmd(cmd)  
        self._groupManager.control_All_Groups()        

def main():
    """Main method called to start the agent."""
    utils.vip_main(facadeIoNMAgent, 
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
