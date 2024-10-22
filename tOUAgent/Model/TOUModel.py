from Model.EnergyModel import EnergyModel
from logging import Logger
class TOUModel(EnergyModel):
    def __init__(self) -> None:
        self._current_hour = 0
        self._actual_consumption = {t: 0 for t in range(24)}  # Initialize actual consumption per hour to zero
        self._tou_rates = []  # TOU rates will be set via the controller
        self._appliances = {}  # Appliances will be set via the controller
        self._ev_charge_required = 12  # Default EV charge required in kWh
        self._ev_min_power = 0  # Default EV minimum power in kW
        self._ev_max_power = 6.0  # Default EV maximum power in kW
        self._target_cost = 15.0  # Default target cost in $
        self._strategy = None
        
    def set_strategy(self, strategy):
        self._strategy=strategy
        
    def execute_strategy(self):
        if self._strategy:
            results=self._strategy.optimize(self)
        else:
            results =[]
            Logger.warning("Stratgey is not set")
        return results
    
    def set_Ev_parameters(self, charge_required, min_power, max_power ):
        self._ev_charge_required= charge_required
        self._ev_max_power = max_power
        self._ev_min_power = min_power
    
    def set_appliances(self, appliances):
        self._appliances=appliances
        
    def set_target_cost(self, target_cost):
        self._target_cost = target_cost
        
    def set_tou_rates(self, tou_rates):
        self._tou_rates = tou_rates
        
    def update_consumption(self)->None:
        pass
    
    