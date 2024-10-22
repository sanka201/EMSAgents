from abc import ABC, abstractmethod

class EnergyModel(ABC):
    def __init__(self) -> None:
        super().__init__()
        
    @abstractmethod
    def update_consumption(self)->None:
        pass
    
    @abstractmethod
    def execute_strategy(self):
        pass
    
    @abstractmethod
    def set_strategy(self,strategy):
        pass
    
    @abstractmethod
    def set_appliances(self,appliances):
        pass
    
    @abstractmethod
    def set_Ev_parameters(self):
        pass