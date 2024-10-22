"""
Agent documentation goes here.
"""

__docformat__ = 'reStructuredText'

import logging
import sys
from datetime import datetime
from volttron.platform.agent import utils
from volttron.platform.scheduling import cron,periodic
from volttron.platform.vip.agent import Agent, Core, RPC
import sys
import requests
import mysql.connector
import json
sys.path.append("/home/sanka/NIRE_EMS/volttron/TOUAgent/tOUAgent/")
from Controller.Controller import Controller 

_log = logging.getLogger(__name__)

utils.setup_logging()
__version__ = "0.1"

# TOU Tariff rates in $/kWh for each hour
tou_rates = [
    0.10, 0.10, 0.10, 0.10, 0.10, 0.10,  # Off-Peak (00:00 - 06:00)
    0.15, 0.15, 0.15, 0.15, 0.15, 0.15,  # Mid-Peak (06:00 - 12:00)
    0.15, 0.15, 0.15, 0.15, 0.30, 0.30,  # Mid-Peak (12:00 - 16:00), Peak (16:00 - 18:00)
    0.30, 0.30, 0.15, 0.15, 0.10, 0.10   # Peak (18:00 - 20:00), Off-Peak (20:00 - 23:59)
]

# Appliance power ratings (kW) and required operation hours
appliances = {
    "building540/NIRE_WeMo_cc_1/w1": {"power": .08, "hours": 2},   # Example: 1 kW power, 2 hours required
    "building540/NIRE_WeMo_cc_1/w2": {"power": .12, "hours": 1},   # Example: 2 kW power, 1 hour required
    "building540/NIRE_WeMo_cc_1/w3": {"power": .43, "hours": 3},   # Example: 1.5 kW power, 3 hours required
    "building540/NIRE_WeMo_cc_1/w4": {"power": .11, "hours": 1},   # Example: 3 kW power, 1 hour required
    "building540/NIRE_WeMo_cc_1/w5": {"power": .34, "hours": 24},    # Example: 0.5 kW power, 4 hours required
    "building540/NIRE_WeMo_cc_1/w6": {"power": .22, "hours": 2},   # Example: 1 kW power, 2 hours required
    "building540/NIRE_WeMo_cc_1/w7": {"power": .23, "hours": 1},   # Example: 2 kW power, 1 hour required
    "building540/NIRE_WeMo_cc_1/w8": {"power": .08, "hours": 3},   # Example: 1.5 kW power, 3 hours required
    "building540/NIRE_WeMo_cc_1/w9": {"power": .175, "hours": 1},   # Example: 3 kW power, 1 hour required
    "building540/NIRE_WeMo_cc_1/w10": {"power": .08, "hours": 4},    # Example: 0.5 kW power, 4 hours required
    "building540/NIRE_WeMo_cc_1/w11": {"power": .14, "hours": 2},   # Example: 1 kW power, 2 hours required
    "building540/NIRE_WeMo_cc_1/w12": {"power": .04, "hours": 1},   # Example: 2 kW power, 1 hour required
    "building540/NIRE_WeMo_cc_1/w13": {"power": .07, "hours": 3},   # Example: 1.5 kW power, 3 hours required
    "building540/NIRE_WeMo_cc_1/w14": {"power": .09, "hours": 1},   # Example: 3 kW power, 1 hour required
    "building540/NIRE_WeMo_cc_1/w15": {"power": 0.19, "hours": 4},    # Example: 0.5 kW power, 4 hours required
    "building540/NIRE_WeMo_cc_4/w1": {"power": .25, "hours": 24},   # Example: 1 kW power, 2 hours required
    "building540/NIRE_WeMo_cc_4/w2": {"power": .12, "hours": 24},   # Example: 2 kW power, 1 hour required
    "building540/NIRE_WeMo_cc_4/w3": {"power": .08, "hours": 24},   # Example: 1.5 kW power, 3 hours required
    "building540/NIRE_WeMo_cc_4/w4": {"power": .05, "hours": 24},   # Example: 3 kW power, 1 hour required
    "building540/NIRE_WeMo_cc_4/w5": {"power": .139, "hours": 24},    # Example: 0.5 kW power, 4 hours required
    "building540/NIRE_WeMo_cc_4/w6": {"power": .03, "hours": 24},   # Example: 1 kW power, 2 hours required
    "building540/NIRE_WeMo_cc_4/w7": {"power": .13, "hours": 24},   # Example: 2 kW power, 1 hour required
    "building540/NIRE_WeMo_cc_4/w8": {"power": .104, "hours": 24},   # Example: 1.5 kW power, 3 hours required
    "building540/NIRE_WeMo_cc_4/w9": {"power": .567, "hours": 24},   # Example: 3 kW power, 1 hour required
    "building540/NIRE_WeMo_cc_4/w10": {"power": 1.4, "hours": 24},    # Example: 0.5 kW power, 4 hours required
    "building540/NIRE_WeMo_cc_4/w11": {"power": .104, "hours": 24},   # Example: 1 kW power, 2 hours required
    "building540/NIRE_ALPHA_cc_2/w1": {"power": .03, "hours": 1},   # Example: 2 kW power, 1 hour required
    "building540/NIRE_ALPHA_cc_2/w2": {"power": .141, "hours": 3},   # Example: 1.5 kW power, 3 hours required
    "building540/NIRE_ALPHA_cc_2/w3": {"power": .07, "hours": 1},   # Example: 3 kW power, 1 hour required
    "building540/NIRE_ALPHA_cc_2/w4": {"power": 0.02, "hours": 4},  
    "building540/NIRE_ALPHA_cc_2/w5": {"power": 0.04, "hours": 12},   # Example: 1 kW power, 2 hours required
    "building540/NIRE_ALPHA_cc_2/w6": {"power": 0.137, "hours": 1},   # Example: 2 kW power, 1 hour required
    "building540/NIRE_ALPHA_cc_2/w7": {"power": 0.145, "hours": 3},   # Example: 1.5 kW power, 3 hours required
    "building540/NIRE_ALPHA_cc_2/w8": {"power": 0.074, "hours": 1},   # Example: 3 kW power, 1 hour required
    "building540/NIRE_ALPHA_cc_2/w9": {"power": 0.031, "hours": 4},    # Example: 0.5 kW power, 4 hours required
    "building540/NIRE_ALPHA_cc_2/w10": {"power": 0.05, "hours": 2},   # Example: 1 kW power, 2 hours required
    "building540/NIRE_ALPHA_cc_2/w11": {"power": 0.11, "hours": 1},   # Example: 2 kW power, 1 hour required
    "building540/NIRE_ALPHA_cc_2/w12": {"power": 0.03, "hours": 3},   # Example: 1.5 kW power, 3 hours required
    "building540/NIRE_ALPHA_cc_2/w13": {"power": 0.14, "hours": 1},   # Example: 3 kW power, 1 hour required
    "building540/NIRE_ALPHA_cc_2/w14": {"power": 0.11, "hours": 4},    # Example: 0.5 kW power, 4 hours required# Example: 0.5 kW power, 4 hours required
    "building540/NIRE_ALPHA_cc_1/w2": {"power": .03, "hours": 4},    # Example: 0.5 kW power, 4 hours required# Example: 0.5 kW power, 4 hours required
    "building540/NIRE_ALPHA_cc_1/w3": {"power": 1.1, "hours": 4}, 
    "building540/NIRE_ALPHA_cc_1/w4": {"power": .05, "hours": 4}, 
    "building540/NIRE_ALPHA_cc_1/w6": {"power": .3, "hours": 4}, 
    "building540/NIRE_ALPHA_cc_1/w17": {"power": 1.415, "hours": 4}, 
    "building540/NIRE_ALPHA_cc_1/w19": {"power": .3, "hours": 4}, 
}



def tOUAgent(config_path, **kwargs):
    """
    Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.
    :type config_path: str
    :returns: Touagent
    :rtype: Touagent
    """
    try:
        config = utils.load_config(config_path)
    except Exception:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    setting1 = int(config.get('setting1', 1))
    setting2 = config.get('setting2', "some/random/topic")

    return Touagent(setting1, setting2, **kwargs)


class Touagent(Agent):
    """
    Document agent constructor here.
    """

    def __init__(self, setting1=1, setting2="some/random/topic", **kwargs):
        super(Touagent, self).__init__(**kwargs)
        _log.debug("vip_identity: " + self.core.identity)

        self.setting1 = setting1
        self.setting2 = setting2

        self.default_config = {"setting1": setting1,
                               "setting2": setting2}

        # Set a default configuration to ensure that self.configure is called immediately to setup
        # the agent.
        self.vip.config.set_default("config", self.default_config)
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
    def cron_function(self):
 
        current_time = datetime.now()
        # Extract the current hour in 24-hour format
        
        current_hour = current_time.hour
        schedule=self._controller.run_optimization(current_hour)
        url = "http://127.0.0.1:8880/api/lmpdata/"
        response = requests.get(url)
        _log.info(f"Sheduling the next hour .......................The current hour in 24-hour format is: {current_hour}")
        

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
        self._controller = Controller()
            # Set configurations based on user input
        self._controller.configure_model(
        tou_rates,
        appliances,
        ev_charge_required=2,  # Example EV charge required
        ev_min_power=0.5,       # Example EV minimum power
        ev_max_power=6.0,       # Example EV maximum power
        target_cost=8.0         # Example target cost
        )
        self.core.schedule(cron('0-59 * * * *'), self.cron_function)
        # Example RPC call
        # self.vip.rpc.call("some_agent", "some_method", arg1, arg2)
        pass

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
    utils.vip_main(tOUAgent, 
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
