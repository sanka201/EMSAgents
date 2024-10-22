"""
Agent documentation goes here.
"""

__docformat__ = 'reStructuredText'
import json
import logging
import mysql.connector
import sys
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, RPC
import pandas as pd
import numpy as np
import seaborn as sns
from datetime import timedelta
from volttron.platform.scheduling import cron,periodic
sys.path.append("/home/sanka/NIRE_EMS/volttron/Windbatterycontrol/windbatterycontrol/")
from EnergyOPtimisationSystem import EnergyOPtimisationSystem
_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"


def windbatterycontrol(config_path, **kwargs):
    """
    Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.
    :type config_path: str
    :returns: Windbatterycontrol
    :rtype: Windbatterycontrol
    """
    try:
        config = utils.load_config(config_path)
    except Exception:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    setting1 = int(config.get('setting1', 1))
    setting2 = config.get('setting2', "some/random/topic")

    return Windbatterycontrol(setting1, setting2, **kwargs)


class Windbatterycontrol(Agent):
    """
    Document agent constructor here.
    """

    def __init__(self, setting1=1, setting2="some/random/topic", **kwargs):
        super(Windbatterycontrol, self).__init__(**kwargs)
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

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        """
        This is method is called once the Agent has successfully connected to the platform.
        This is a good place to setup subscriptions if they are not dynamic or
        do any other startup activities that require a connection to the message bus.
        Called after any configurations methods that are called at startup.

        Usually not needed if using the configuration store.
        """
        self.shedule_reset=0
        self.EV_cmd=7.2
        self.low_cmd=1.6
        self.medium_cmd=2.8
        self.critical_cmd=2.8
        self.low_cmd2=1.6
        self.medium_cmd2=2.8
        self.critical_cmd2=2.8
        self.Prev_Ev_charge_power=-1
        self.battery_discharge_power=0
        self.battery_charge=0
        self.windturbine_running=1
        #self.core.periodic(40,self.dowork)
        self.core.schedule(cron('*/1 * * * *'), self.cron_function)    
        self.core.schedule(cron('*/3 * * * *'), self.load_control_function)

    def load_control_function(self): 
        self.low_cmd2=self.low_cmd
        self.medium_cmd2=self.medium_cmd
        self.critical_cmd2=self.critical_cmd  
    def reset_wind_turbine(self):
        self.windturbine_running=1


    def cron_function(self):

  
        SOC=self.vip.rpc.call('storageAgentagent-0.1_1','get_batter1_SOC').get(timeout=20)
        ems = EnergyOPtimisationSystem()

        # Define simulation parameters
        initial_SOC = 100.0  # Starting with a fully charged battery
        num_scenarios = 10    # Total number of scenarios to simulate
        grid_failure_scenarios = [False, False, True, True, False, False, False, True, True, False]  # Grid failure scenarios
        ev_availability = np.random.choice([True, False], size=num_scenarios, p=[0.7, 0.3])
        
        # Generate varying wind power levels (e.g., fluctuating between 0 and 10 kW)
        time_steps = np.arange(1, num_scenarios + 1)
        wind_power_levels = 5 + 5 * np.sin(2 * np.pi * time_steps / num_scenarios)  # Wind power between 0 and 10 kW
        wind_power_levels += np.random.normal(0, 1, num_scenarios)
        wind_power_levels = np.clip(wind_power_levels, 0, None)  # Ensure wind power is non-negative
        results=self.vip.rpc.call('facadeAgentagent-0.1_1','get_Facades_Consumption','Django').get(timeout=20)
        total_consumption=results['5']+results['6']+results['7']+results['4']
        if SOC >= 99:
            windpower=0
            self.windturbine_running=0
            self.shedule_reset=1
        elif SOC <=95 and self.shedule_reset==1:
            self.core.schedule(utils.get_aware_utc_now() + timedelta(minutes=5), self.reset_wind_turbine)
            self.shedule_reset=0
        else:pass
        
        if self.windturbine_running==1:
                  windpower=self.fetch_wind_data()
        else:
                  windpower=0
        
        if (results['4'] > 0.5 and self.Prev_Ev_charge_power >0) or self.Prev_Ev_charge_power==-1:
            ems.run_optimization(SOC_current=SOC, wind_power=int(windpower)/1000, EV_available=True, grid_failure=False,user_prefers_EV_over_critical=True)
        else:
            ems.run_optimization(SOC_current=SOC, wind_power=int(windpower)/1000, EV_available=True, grid_failure=False,user_prefers_EV_over_critical=False)
        print(ems.results[0]['Battery_Charge_kW'],ems.results[0]['Served_Low_Load_kW'],ems.results[0]['Served_Medium_Load_kW'],ems.results[0]['Served_Critical_Load_kW'])
        print(ems.results)
        self.Prev_Ev_charge_power=ems.results[0]['Served_EV_Load_kW']
        self.EV_cmd=ems.results[0]['Served_EV_Load_kW']
        self.low_cmd=ems.results[0]['Served_Low_Load_kW']
        self.medium_cmd=ems.results[0]['Served_Medium_Load_kW']
        self.critical_cmd=ems.results[0]['Served_Critical_Load_kW']
        result=self.vip.rpc.call('gLEAMMNIREAgentagent-0.1_1','execute_Control_by_Priority_Groups_nire',{'4':('lpc',self.EV_cmd*1000), '5':('lpc',self.low_cmd2*1000),'6':('lpc',self.medium_cmd2*1000),'7':('lpc',self.critical_cmd2*1000)},'Django').get(timeout=20)
        if  ems.results[0]['Battery_Charge_kW']>0:
            self.battery_charge=1
            result=self.vip.rpc.call('storageAgentagent-0.1_1','charge_battery1',ems.results[0]['Battery_Charge_kW']*1000,0.016).get(timeout=20)
        elif (ems.results[0]['Wind_Power_kW']-total_consumption)>0:
             self.vip.rpc.call('storageAgentagent-0.1_1','charge_battery1', ems.results[0]['Wind_Power_kW']*1000-total_consumption+ems.results[0]['Battery_Charge_kW']*1000,0.06).get(timeout=20)# max(0, self.current_soc - total_consumption)
             ems.results[0]['Battery_Charge_kW']= ems.results[0]['Wind_Power_kW']-total_consumption/1000+ems.results[0]['Battery_Charge_kW']    
        elif ems.results[0]['Battery_Discharge_kW']>0:
             self.vip.rpc.call('storageAgentagent-0.1_1','discharge_battery1', total_consumption-ems.results[0]['Wind_Power_kW']*1000,0.06).get(timeout=20)# max(0, self.current_soc - total_consumption)
             ems.results[0]['Battery_Discharge_kW']= total_consumption/1000-ems.results[0]['Wind_Power_kW']
             print('Discharging.........................................................', total_consumption-ems.results[0]['Wind_Power_kW']*1000)
        result = self.vip.pubsub.publish(peer='pubsub',topic= 'record/'+str(self.core.identity)+'/NIREEMS/Wind_battery_control', message=ems.results[0]) 
    def get_connection(self):
 
        connection = mysql.connector.connect(
            host='192.168.10.52',
            user='SANKA',
            password='3Sssmalaka@!',
            database='GLEAMM_NIRE_meters'
        )
        return connection
    
    def fetch_wind_data(self):

        conn= self.get_connection()
        cursor = conn.cursor()
        # Query to get all necessary data
        query =""" SELECT ts, value_string FROM GLEAMM_NIRE_meters.data  where topic_id=1  ORDER BY ts DESC LIMIT 1"""        
        cursor.execute(query)
        result = cursor.fetchall()
        ts, value_string=result[0]
        
        data =json.loads(value_string)
        
        power=data.get('wind', {}).get('Bergey', {}).get('inverter_output_power', None)
        return power        

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
    utils.vip_main(windbatterycontrol, 
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
