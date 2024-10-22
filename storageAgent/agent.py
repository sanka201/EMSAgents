"""
Agent documentation goes here.
"""

__docformat__ = 'reStructuredText'

import logging
import sys
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC
sys.path.append("/home/sanka/NIRE_EMS/volttron/LoadPriorityControl/LPCv1/")
from Model.BatterySim import Battery
_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"


def storageAgent(config_path, **kwargs):
    """
    Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.
    :type config_path: str
    :returns: Storageagent
    :rtype: Storageagent
    """
    try:
        config = utils.load_config(config_path)
    except Exception:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    setting1 = int(config.get('setting1', 1))
    setting2 = config.get('setting2', "some/random/topic")

    return Storageagent(setting1, setting2, **kwargs)


class Storageagent(Agent):
    """
    Document agent constructor here.
    """

    def __init__(self, setting1=1, setting2="some/random/topic", **kwargs):
        super(Storageagent, self).__init__(**kwargs)
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
        message={'storage':{'battery1':self.get_batter1_SOC(),'battery2':self.get_batter2_SOC()}}
        result = self.vip.pubsub.publish(peer='pubsub',topic= 'record/'+str(self.core.identity)+'/NIREEMS/data', message=message) 
        print('44444444444444444444444444444444444444444444444444444444333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333388888888888888888888888888888888888888888888888888888888888888888888888888//////////////////')
        
    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        """
        This is method is called once the Agent has successfully connected to the platform.
        This is a good place to setup subscriptions if they are not dynamic or
        do any other startup activities that require a connection to the message bus.
        Called after any configurations methods that are called at startup.

        Usually not needed if using the configuration store.
        """
        
        self.battery1 = None

        self.battery2 = None

    @Core.receiver("onstop")
    def onstop(self, sender, **kwargs):
        """
        This method is called when the Agent is about to shutdown, but before it disconnects from
        the message bus.
        """
        pass

    @RPC.export
    def config_battery1(self, capacity_kWh, max_discharge_kW, initial_soc,min_soc_percent):
        
        del self.battery1
        self.battery1 = Battery(
            capacity_kWh=capacity_kWh,             # Battery capacity in kWh
            max_discharge_kW=max_discharge_kW,          # Max discharge power in kW
            voltage_nominal=55.1,          # Nominal voltage in Volts
            peukert_exponent=1.05,        # Peukert's exponent
            initial_charge_efficiency=0.95,       # Initial charging efficiency
            initial_discharge_efficiency=0.95,    # Initial discharging efficiency
            initial_soc=initial_soc,              # Initial State of Charge (50%)
            state_of_health=0.98,         # Battery health (98%)
            temperature_C=30,             # Temperature in Celsius
            min_soc_percent=min_soc_percent            # Minimum SoC percentage
        )
    
    @RPC.export
    def config_battery2(self, capacity_kWh, max_discharge_kW, initial_soc,min_soc_percent):
        
        del self.battery2
        self.battery2 = Battery(
            capacity_kWh=capacity_kWh,             # Battery capacity in kWh
            max_discharge_kW=max_discharge_kW,         # Max discharge power in kW
            voltage_nominal=800,          # Nominal voltage in Volts
            peukert_exponent=1.05,        # Peukert's exponent
            initial_charge_efficiency=0.95,       # Initial charging efficiency
            initial_discharge_efficiency=0.95,    # Initial discharging efficiency
            initial_soc=initial_soc,              # Initial State of Charge (50%)
            state_of_health=0.98,         # Battery health (98%)
            temperature_C=30,             # Temperature in Celsius
            min_soc_percent=min_soc_percent            # Minimum SoC percentage
        )
        
    @RPC.export
    def charge_battery1(self, surplus_power_W,duration_h):
         batt1_charge_power = self.battery1.charge(surplus_power_W , duration_h)
         return self.get_batter1_SOC() 

    @RPC.export
    def charge_battery2(self, surplus_power_W,duration_h):
         batt2_charge_power = self.battery2.charge(surplus_power_W, duration_h)
         return self.get_batter2_SOC() 
              
    @RPC.export
    def discharge_battery1(self, load,duration_h):
         power_from_battery1  = self.battery1.discharge(load, duration_h)
         return self.get_batter1_SOC() 

    @RPC.export
    def discharge_battery2(self, load,duration_h):
         power_from_battery2  = self.battery2.discharge(load , duration_h)
         return self.get_batter2_SOC()  

    @RPC.export
    def get_batter1_SOC(self):
         return self.battery1.get_soc_percent()      

    @RPC.export
    def get_batter2_SOC(self):
         return self.battery2.get_soc_percent()
           
def main():
    """Main method called to start the agent."""
    utils.vip_main(storageAgent, 
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
