"""
Agent documentation goes here.
"""

__docformat__ = 'reStructuredText'

import logging
import sys, time
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
from Controller.DeviceMonitor import DeviceMonitor
from Model.EVCharger import EVCharger
from Controller.EvMonitor import EvMonitor
from Model.SmartPlugDataService  import SmartPlugDataService
from Model.GroupRepository import GroupRepository
_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"


def gLEAMMNIREAgent(config_path, **kwargs):
    """
    Parses the Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.
    :type config_path: str
    :returns: Gleammnireagent
    :rtype: Gleammnireagent
    """
    try:
        config = utils.load_config(config_path)
    except Exception:
        config = {}

    if not config:
        _log.info("Using Agent defaults for starting configuration.")

    setting1 = int(config.get('setting1', 1))
    setting2 = config.get('setting2', "some/random/topic")

    return Gleammnireagent(setting1, setting2, **kwargs)


class Gleammnireagent(Agent):
    """
    Document agent constructor here.
    """

    def __init__(self, setting1=1, setting2="some/random/topic", **kwargs):
        super(Gleammnireagent, self).__init__(**kwargs)
        _log.debug("vip_identity: " + self.core.identity)

        self.setting1 = setting1
        self.setting2 = setting2

        self.default_config = {"setting1": setting1,
                               "setting2": setting2}
        self.repository = GroupRepository(self.vip,self.core.identity)
        self.smart_Plug_Data_service= SmartPlugDataService(self.repository)
        # Set a default configuration to ensure that self.configure is called immediately to setup
        # the agent.
        self.controllerinprocess=0
        self.periodiccontrol=1
        self.vip.config.set_default("config", self.default_config)
        self.task_handle=self.core.periodic(60,self.dowork)
        self.core.periodic(40,self.publish)
        # Hook self.configure up to changes to the configuration file "config".
        self.vip.config.subscribe(self.configure, actions=["NEW", "UPDATE"], pattern="config")

    def retrieve_configuration(self,config_name):
        """
        Retrieve the CSV configuration from the configuration store.
        """
        # Get the configuration data directly as a Python list of dictionaries
        csv_data = self.vip.config.get(config_name)
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
                                  callback=self._handle_publish, all_platforms=True)

    def _handle_publish(self, peer, sender, bus, topic, headers, message):
        """
        Callback triggered by the subscription setup using the topic from the agent's config file
        """
        if    self.controllerinprocess==0:
            if "/EV/" in topic :
                self._eVmonitor.process_Message({'topic':topic, 'message':message})
            elif "building540" in topic:
                self._niremonitor.process_Message({'topic':topic, 'message':message})
                pass
            elif "GLEAMM" in topic:
                self._gleammmonitor.process_Message({'topic':topic, 'message':message})
        else:
            pass

    def dowork(self):

        print("HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH  /t /t /n HHHHHHHHHHHHHHHHH/n NNNNNNNN/N /n hhhhhhhhh")
        if (self._group_mode_selector==0  and         self.controllerinprocess==0) and self.periodiccontrol==1 :
            self.controllerinprocess=1
            self._groupManager.control_All_Groups()
            self.controllerinprocess=0     
        elif (self._group_mode_selector==1  and         self.controllerinprocess==0) and self.periodiccontrol==1  :
            self.controllerinprocess=1
            self._groupManager.execute_Strategy()
            self.controllerinprocess=0    
        self.periodiccontrol=1          
    def publish(self):
        self.smart_Plug_Data_service.create_and_store_smart_plug_json(self._gleammgroup)            
        
    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        """
        This is method is called once the Agent has successfully connected to the platform.
        This is a good place to setup subscriptions if they are not dynamic or
        do any other startup activities that require a connection to the message bus.
        Called after any configurations methods that are called at startup.

        Usually not needed if using the configuration store.
        """
        self._niregroup = IoTDeviceGroup() # Group Facade
        self._niremonitor = DeviceMonitor() # Monitor for smart plug update
        self._eVmonitor = EvMonitor() # Monitor for EV charging station
        self._groupManager = IoTDeviceGroupManager()
        self._gleammmonitor = GLEAMMMonitor() # Monitor for smart plug update
        self._gleammgroup = IoTDeviceGroup()
        self._group_mode_selector=0  
        niredevicelist=self.retrieve_configuration('NIREAssets')
        gleammdevicelist=self.retrieve_configuration('GLEAMMAssets')
        for item in niredevicelist:
            asset=SmartPlug(item['Device'],self.vip)
            asset._max_power_rating=int(item['Maxpower'])
            asset._power_multiply_factor=float(item['Mulitplyfactor'])
            asset._priority =int(item['Priority'])
            self._niregroup.add_Device(asset)
            self._niremonitor.register_Observer(asset)
        for item in gleammdevicelist:
            asset=SmartPlug(item['Device'],self.vip)
            asset._max_power_rating=int(item['Maxpower'])
            asset._deviceType='gleammrload'
            asset._power_multiply_factor=float(item['Mulitplyfactor'])
            asset._priority =int(item['Priority'])
            self._gleammgroup.add_Device(asset)
            self._gleammmonitor.register_Observer(asset)
        self.ev_charger= EVCharger('building540/EV/JuiceBox',self.vip)
        self._eVmonitor.register_Observer(self.ev_charger)
        self._niregroup.add_Device(self.ev_charger)           
        self._groupManager.add_Group( self._niregroup)
        self._groupManager.add_Group( self._gleammgroup)
        self._groupManager.group_By_Priority()
        self._groupManager.control_All_Groups_set_cmd(('lpc',77000))  

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
        self.periodiccontrol=0     
        self.controllerinprocess=1
        if self.task_handle:
            self.task_handle.kill()     
            self.task_handle = None
        self._groupManager.add_Group( self._niregroup)
        self._groupManager.add_Group( self._gleammgroup)
        self.smart_Plug_Data_service.store_Control_Commands(cmd,'All_Groups')
        self.vip.rpc.call('facadeAgentagent-0.1_1','update_control_command',('lpc',None),'Django').get(timeout=20)
        self.smart_Plug_Data_service.store_Control_Commands(('lpc',None),'GLEAMM')  
        self.smart_Plug_Data_service.create_and_store_smart_plug_json(self._gleammgroup)
        self._group_mode_selector=0  
        self._groupManager.control_All_Groups_set_cmd(cmd)  
        self._groupManager.control_All_Groups()
        self.controllerinprocess=0
        self.task_handle=self.core.periodic(60,self.dowork)
        
    @RPC.export
    def execute_Control_all_Groups_nire(self,cmd:dict,sender)->None:
        self.periodiccontrol=0  
        self.controllerinprocess=1
        if self.task_handle:
            self.task_handle.kill()      
            self.task_handle = None
        self._groupManager.remove_Group( self._gleammgroup) 
        self._groupManager.add_Group( self._niregroup) 
        self.vip.rpc.call('facadeAgentagent-0.1_1','update_control_command',cmd,'Django').get(timeout=20)
        self.smart_Plug_Data_service.store_Control_Commands(('lpc',None),'Django')
        self.smart_Plug_Data_service.create_and_store_smart_plug_json(self._gleammgroup)
        self._group_mode_selector=0  
        self._groupManager.control_All_Groups_set_cmd(cmd)  
        self._groupManager.control_All_Groups()
        self.controllerinprocess=0  
        self.task_handle=self.core.periodic(60,self.dowork)
    def schedule_periodic_task(self):
        """Assign the periodic task to run every 60 seconds after the first delay."""
        self.periodic_task = self.core.periodic(60, self.dowork)              
    @RPC.export
    def execute_Control_all_Groups_GLEAMM(self,cmd:dict,sender)->None:
        self.controllerinprocess=1
        self.periodiccontrol=0     
        if self.task_handle:
            self.task_handle.kill()       
            self.task_handle = None
        self._groupManager.remove_Group( self._niregroup)
        self._groupManager.add_Group( self._gleammgroup) 
        self.vip.rpc.call('facadeAgentagent-0.1_1','update_control_command',('lpc',None),'Django').get(timeout=20)       
        self.smart_Plug_Data_service.store_Control_Commands(cmd,'GLEAMM')
        self.smart_Plug_Data_service.create_and_store_smart_plug_json(self._gleammgroup)
        self._group_mode_selector=0  
        self._groupManager.control_All_Groups_set_cmd(cmd)  
        self._groupManager.control_All_Groups()
        self.controllerinprocess=0
        self.task_handle=self.core.periodic(60,self.dowork)

    @RPC.export
    def execute_Control_by_Priority_Groups_nire(self,cmd:dict,sender)->None:
        """
        cmd : power consumption threshold and the control stratgey for for each priority group. ex: {'1':('simplecontrol',300),'2':('directcontrol',400)} 
        Thsi Method sorts the groups pased on priorities and create new sets of groups for differernt priorities
        Then it asssign the control stratagy for the each group
        """
        self.periodiccontrol=0  
        self.controllerinprocess=1
        if self.task_handle:
            self.task_handle.kill()     
            self.task_handle = None
        self._groupManager.add_Group( self._niregroup)
        self._groupManager.add_Group( self._gleammgroup)
        self.vip.rpc.call('facadeAgentagent-0.1_1','update_control_command',cmd,'Django').get(timeout=20)
        self.smart_Plug_Data_service.store_Control_Commands(('lpc',None),'GLEAMM')  
        self.smart_Plug_Data_service.create_and_store_smart_plug_json(self._niregroup)
        self._group_mode_selector=1
        print("Recived Control Command>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",self._groupManager.group_By_Priority())
        priorityGroups=self._groupManager.group_By_Priority()
        self._groupManager.clear_Groups_Stratgies()
        for key in cmd.keys(): 
            print("Recived Control Command>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",priorityGroups[int(key)],cmd)
            self._groupManager.set_Group_Stratagy(priorityGroups[int(key)],cmd[key])
        self._groupManager.execute_Strategy()
        self.controllerinprocess=0
        self.task_handle=self.core.periodic(60,self.dowork)        
    @RPC.export
    def execute_Control_by_Priority_Groups_GLEAMM(self,cmd:dict,sender)->None:
        """
        cmd : power consumption threshold and the control stratgey for for each priority group. ex: {'1':('simplecontrol',300),'2':('directcontrol',400)} 
        Thsi Method sorts the groups pased on priorities and create new sets of groups for differernt priorities
        Then it asssign the control stratagy for the each group
        """
        self.periodiccontrol=0  
        self.controllerinprocess=1        
        if self.task_handle:
            self.task_handle.kill()        
            self.task_handle = None
        self._groupManager.remove_Group( self._niregroup)
        self._groupManager.add_Group( self._gleammgroup) 
        self.vip.rpc.call('facadeAgentagent-0.1_1','update_control_command',('lpc',None),'Django').get(timeout=20)  
        self.smart_Plug_Data_service.store_Control_Commands(cmd,'GLEAMM')
        self.smart_Plug_Data_service.create_and_store_smart_plug_json(self._gleammgroup)
        self._group_mode_selector=1
        print("Recived Control Command>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",self._groupManager.group_By_Priority())
        priorityGroups=self._groupManager.group_By_Priority()
        self._groupManager.clear_Groups_Stratgies()
        for key in cmd.keys(): 
            print("Recived Control Command>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",priorityGroups[int(key)],cmd)
            self._groupManager.set_Group_Stratagy(priorityGroups[int(key)],cmd[key])
        self._groupManager.execute_Strategy()
        self.controllerinprocess=0
        self.task_handle=self.core.periodic(60,self.dowork)          
    @RPC.export
    def execute_Control_by_Priority_Groups_all(self,cmd:dict,sender)->None:
        """
        cmd : power consumption threshold and the control stratgey for for each priority group. ex: {'1':('simplecontrol',300),'2':('directcontrol',400)} 
        Thsi Method sorts the groups pased on priorities and create new sets of groups for differernt priorities
        Then it asssign the control stratagy for the each group
        """
        self.periodiccontrol=0  
        self.controllerinprocess=1
        if self.task_handle:
            self.task_handle.kill()      
            self.task_handle = None
        self._groupManager.add_Group( self._niregroup)
        self._groupManager.add_Group( self._gleammgroup)
        self.smart_Plug_Data_service.store_Control_Commands(cmd,'All_Groups')  
        self.vip.rpc.call('facadeAgentagent-0.1_1','update_control_command',('lpc',None),'Django').get(timeout=20)  
        #self.smart_Plug_Data_service.create_and_store_smart_plug_json(self._group)
        self._group_mode_selector=1
        print("Recived Control Command>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",self._groupManager.group_By_Priority())
        priorityGroups=self._groupManager.group_By_Priority()
        self._groupManager.clear_Groups_Stratgies()
        for key in cmd.keys(): 
            print("Recived Control Command>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>",priorityGroups[int(key)],cmd)
            self._groupManager.set_Group_Stratagy(priorityGroups[int(key)],cmd[key])
        self._groupManager.execute_Strategy()
        self.controllerinprocess=0
        self.task_handle=self.core.periodic(60,self.dowork) 
def main():
    """Main method called to start the agent."""
    utils.vip_main(gLEAMMNIREAgent, 
                   version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
