"""
Agent documentation goes here.
"""

__docformat__ = 'reStructuredText'

import logging
import sys
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC
from volttron.platform.scheduling import cron,periodic
sys.path.append("/home/sanka/NIRE_EMS/volttron/LoadPriorityControl/LPCv1/")
from Controller.ResiliencyControllerv1 import BatteryOptimizer
_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"


def reciliencyControlAgent(config_path, **kwargs):
    """
    Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.
    :type config_path: str
    :returns: Reciliencycontrolagent
    :rtype: Reciliencycontrolagent
    """
    try:
        config = utils.load_config(config_path)
    except Exception:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    setting1 = int(config.get('setting1', 1))
    setting2 = config.get('setting2', "some/random/topic")

    return Reciliencycontrolagent(setting1, setting2, **kwargs)


class Reciliencycontrolagent(Agent):
    """
    Document agent constructor here.
    """

    def __init__(self, setting1=1, setting2="some/random/topic", **kwargs):
        super(Reciliencycontrolagent, self).__init__(**kwargs)
        _log.debug("vip_identity: " + self.core.identity)

        self.setting1 = setting1
        self.setting2 = setting2

        self.default_config = {"setting1": setting1,
                               "setting2": setting2}

        # Set a default configuration to ensure that self.configure is called immediately to setup
        # the agent.
        self.vip.config.set_default("config", self.default_config)
        self.core.periodic(40,self.dowork)
        # Hook self.configure up to changes to the configuration file "config".
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")

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
            setting2 = str(config["setting2"])
        except ValueError as e:
            _log.error("ERROR PROCESSING CONFIGURATION: {}".format(e))
            return

        self.setting1 = setting1
        self.setting2 = setting2

        self._create_subscriptions(self.setting2)

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
        pass
    def dowork(self):
        results=self.vip.rpc.call('facadeAgentagent-0.1_1','get_Facades_Consumption','Django').get(timeout=20)
        total_consumption=results['5']+results['6']+results['7']
        self.vip.rpc.call('storageAgentagent-0.1_1','discharge_battery1',total_consumption,0.13).get(timeout=20)# max(0, self.current_soc - total_consumption)
        
    
    def cron_function(self):

        print('************************************************* Croning *********************************************')
                        # Actual consumption data per hour
        actual_consumption_data = [
            {'critical': 1, 'medium': 1, 'low': 2},
            {'critical': 2, 'medium': 1, 'low': 0},  # Low priority load shed
            {'critical': 2.5, 'medium': 0, 'low': 0},  # Medium and low priority loads shed
            # Add more data if needed
        ] 
        #'P_critical_Optimized': 2.1, 'P_medium_Optimized': 0.9, 'P_low_Optimized': 0.9,
        #result=self.vip.rpc.call('gLEAMMNIREAgentagent-0.1_1','execute_Control_all_Groups_nire',('lpc',3700),'Django').get(timeout=20)
        #result=agent.vip.rpc.call('gLEAMMNIREAgentagent-0.1_1','execute_Control_by_Priority_Groups_nire',{'4':('lpc',2000), '5':('lpc',results['P_low_Optimized']),'6':('lpc',results['P_medium_Optimized']),'7':('lpc',results['P_critical_Optimized'])},'Django').get(timeout=20)      
        results = self.optimizer.optimize()  
        result=self.vip.rpc.call('gLEAMMNIREAgentagent-0.1_1','execute_Control_by_Priority_Groups_nire',{'4':('lpc',0), '5':('lpc',results['P_low_Optimized']*1000),'6':('lpc',results['P_medium_Optimized']*1000),'7':('lpc',results['P_critical_Optimized']*1000)},'Django').get(timeout=20)
        print(results)       


    

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        """
        This is method is called once the Agent has successfully connected to the platform.
        This is a good place to setup subscriptions if they are not dynamic or
        do any other startup activities that require a connection to the message bus.
        Called after any configurations methods that are called at startup.

        Usually not needed if using the configuration store.
        """
        self.core.schedule(cron('*/5 * * * *'), self.cron_function)
        #evry 5 minute */5 * * * *
        # every nth over 5th minute 5 */N * * *
        
        n_hours = 1  # Number of hours to optimize ahead in each step
        battery_capacity = 100  # Total battery capacity in kWh
        initial_soc = 100       # Initial SOC in kWh

        # Maximum possible loads for each priority group in kW
        max_loads = {
            'critical': 3,
            'medium': 1.2,
            'low': 3
        }

        # Weights for the objective function
        weights = {
            'critical': 100,
            'medium': 10,
            'low': 1
        }

        # Actual consumption data per hour
        actual_consumption_data = [
            {'critical': 1, 'medium': 1, 'low': 2},
            {'critical': 2, 'medium': 1, 'low': 0},  # Low priority load shed
            {'critical': 2.5, 'medium': 0, 'low': 0},  # Medium and low priority loads shed
            # Add more data if needed
        ]
        # Create an optimizer instance
        self.optimizer = BatteryOptimizer(n_hours, battery_capacity, initial_soc, max_loads, weights,self.vip)
        

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


def main():
    """Main method called to start the agent."""
    utils.vip_main(reciliencyControlAgent, 
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
