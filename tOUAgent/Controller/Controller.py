import sys
sys.path.append("/home/sanka/NIRE_EMS/volttron/TOUAgent/tOUAgent/")
import mysql.connector
from Model.TOU import TOU
from Model.TOUModel import TOUModel
import json
from datetime import datetime
#import requests
import pandas as pd
# Database connection setup





class Controller():
    def __init__(self) -> None:
        self._model= TOUModel()
        
        
    def configure_model(self,tou_rates, appliances, ev_charge_required, ev_min_power, ev_max_power, target_cost):
        self._model.set_appliances(appliances)
        self._model.set_Ev_parameters(ev_charge_required, ev_min_power, ev_max_power)
        self._model.set_target_cost(target_cost)
        self._model.set_tou_rates(tou_rates)
        
    def run_optimization(self,current_hour ):
        self._model.set_strategy(TOU())
        self._model._current_hour = 0 #current_hour
        self._calculate_the_power_consumption(current_hour)
               # Simulate the system dynamically adjusting after each hour
            # Simulate random actual consumption exceeding the threshold in some hours
        appliance_vars,ev_power_vars,power_thresholds =self._model.execute_strategy()
        schedule=0
        return schedule
        
        
    def _calculate_the_power_consumption(self,current_hour):
        connection=mysql.connector.connect(
            host='192.168.128.10',
            user='SANKA',
            password='3Sssmalaka@!',
            database='GLEAMM_NIRE'
        )
        cursor = connection.cursor()

        query =""" SELECT ts, value_string FROM GLEAMM_NIRE.data  where topic_id=5 and  ts <= UTC_TIMESTAMP()   and ts >=date_sub( UTC_TIMESTAMP() , interval 1 hour) ORDER BY ts DESC """
        #query = """ SELECT ts, value_string FROM data WHERE topic_id = 5 ORDER BY ts DESC LIMIT 300 """
        cursor.execute(query)
        rows = cursor.fetchall()

        data_list = []
        total_consumption=0
        for row in rows:
            ts, value_string = row
            data = json.loads(value_string)
            data_list.append((ts, data))
        prevts=0
        sec=0
        
        filtered_tuples = [tup[1]['LMP'] for tup in data_list]
        lmp_average_for_last_hour=sum(filtered_tuples)/1000/len(filtered_tuples)
        
        priority_trend_list = []
        for ts, data in data_list:
            for monitor, buildings in data.get('Monitor', {}).items():
                for building, devices in buildings.items():
                    for device, metrics in devices.items():
                        priority_trend_list.append({
                            'timestamp': ts,
                            'priority': metrics.get('priority'),
                            'power': metrics.get('power'),
                        })
            # Handle EV data
            for ev_device, metrics in data.get('Monitor', {}).get('EV', {}).items():
                priority_trend_list.append({
                    'timestamp': ts,
                    'priority': metrics.get('priority'),
                    'power' : round(metrics.get('power'),1),
                })

        df_priority_trend = pd.DataFrame(priority_trend_list)
        Last_hour_power_consumption=df_priority_trend['power'].sum()/1000* 40 / 3600
        self._model._actual_consumption[current_hour-1] = round(Last_hour_power_consumption,4)

if __name__ == "__main__":
    # Create a controller instance
      
    controller = Controller()

 

            
    # Set configurations based on user input
    controller.configure_model(
        tou_rates,
        appliances,
        ev_charge_required=2,  # Example EV charge required
        ev_min_power=0.5,       # Example EV minimum power
        ev_max_power=6.0,       # Example EV maximum power
        target_cost=10.0         # Example target cost
    )

    # Run optimization
    time_slots = range(2)
    for current_hour in time_slots:
        controller.run_optimization(current_hour)