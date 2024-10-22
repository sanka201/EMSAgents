from pulp import LpMinimize, LpProblem, LpVariable, lpSum, LpBinary, value
from EnergyModel import EnergyModel
# Define initial parameters
time_slots = range(2)  # 24 hours in a day

# TOU Tariff rates in $/kWh for each hour
tou_rates = [
    0.10, 0.10, 0.10, 0.10, 0.10, 0.10,  # Off-Peak (00:00 - 06:00)
    0.15, 0.15, 0.15, 0.15, 0.15, 0.15,  # Mid-Peak (06:00 - 12:00)
    0.15, 0.15, 0.15, 0.15, 0.30, 0.30,  # Mid-Peak (12:00 - 16:00), Peak (16:00 - 18:00)
    0.30, 0.30, 0.15, 0.15, 0.10, 0.10   # Peak (18:00 - 20:00), Off-Peak (20:00 - 23:59)
]

# Appliance power ratings (kW) and required operation hours
appliances = {
    "Appliance_1": {"power": .08, "hours": 24},   # Example: 1 kW power, 2 hours required
    "Appliance_2": {"power": .12, "hours": 1},   # Example: 2 kW power, 1 hour required
    "Appliance_3": {"power": .43, "hours": 3},   # Example: 1.5 kW power, 3 hours required
    "Appliance_4": {"power": .11, "hours": 1},   # Example: 3 kW power, 1 hour required
    "Appliance_5": {"power": .34, "hours": 24},    # Example: 0.5 kW power, 4 hours required
    "Appliance_6": {"power": .22, "hours": 2},   # Example: 1 kW power, 2 hours required
    "Appliance_7": {"power": .23, "hours": 1},   # Example: 2 kW power, 1 hour required
    "Appliance_8": {"power": .08, "hours": 3},   # Example: 1.5 kW power, 3 hours required
    "Appliance_9": {"power": .175, "hours": 1},   # Example: 3 kW power, 1 hour required
    "Appliance_10": {"power": .08, "hours": 4},    # Example: 0.5 kW power, 4 hours required
    "Appliance_11": {"power": .14, "hours": 2},   # Example: 1 kW power, 2 hours required
    "Appliance_12": {"power": .04, "hours": 1},   # Example: 2 kW power, 1 hour required
    "Appliance_13": {"power": .07, "hours": 3},   # Example: 1.5 kW power, 3 hours required
    "Appliance_14": {"power": .09, "hours": 1},   # Example: 3 kW power, 1 hour required
    "Appliance_15": {"power": 0.19, "hours": 4},    # Example: 0.5 kW power, 4 hours required
    "Appliance_16": {"power": .25, "hours": 2},   # Example: 1 kW power, 2 hours required
    "Appliance_17": {"power": .12, "hours": 1},   # Example: 2 kW power, 1 hour required
    "Appliance_18": {"power": .08, "hours": 3},   # Example: 1.5 kW power, 3 hours required
    "Appliance_19": {"power": .05, "hours": 1},   # Example: 3 kW power, 1 hour required
    "Appliance_20": {"power": .139, "hours": 4},    # Example: 0.5 kW power, 4 hours required
    "Appliance_21": {"power": .03, "hours": 24},   # Example: 1 kW power, 2 hours required
    "Appliance_22": {"power": .13, "hours": 1},   # Example: 2 kW power, 1 hour required
    "Appliance_23": {"power": .104, "hours": 3},   # Example: 1.5 kW power, 3 hours required
    "Appliance_24": {"power": .567, "hours": 21},   # Example: 3 kW power, 1 hour required
    "Appliance_25": {"power": 1.4, "hours": 14},    # Example: 0.5 kW power, 4 hours required
    "Appliance_26": {"power": .104, "hours": 2},   # Example: 1 kW power, 2 hours required
    "Appliance_27": {"power": .03, "hours": 1},   # Example: 2 kW power, 1 hour required
    "Appliance_28": {"power": .141, "hours": 3},   # Example: 1.5 kW power, 3 hours required
    "Appliance_29": {"power": .07, "hours": 1},   # Example: 3 kW power, 1 hour required
    "Appliance_30": {"power": 0.02, "hours": 4},  
    "Appliance_31": {"power": 0.04, "hours": 12},   # Example: 1 kW power, 2 hours required
    "Appliance_32": {"power": 0.137, "hours": 1},   # Example: 2 kW power, 1 hour required
    "Appliance_33": {"power": 0.145, "hours": 3},   # Example: 1.5 kW power, 3 hours required
    "Appliance_34": {"power": 0.074, "hours": 1},   # Example: 3 kW power, 1 hour required
    "Appliance_35": {"power": 0.031, "hours": 4},    # Example: 0.5 kW power, 4 hours required
    "Appliance_36": {"power": 0.05, "hours": 2},   # Example: 1 kW power, 2 hours required
    "Appliance_37": {"power": 1.1, "hours": 1},   # Example: 2 kW power, 1 hour required
    "Appliance_38": {"power": 0.05, "hours": 3},   # Example: 1.5 kW power, 3 hours required
    "Appliance_39": {"power": 0.03, "hours": 1},   # Example: 3 kW power, 1 hour required
    "Appliance_40": {"power": 1.415, "hours": 4},    # Example: 0.5 kW power, 4 hours required# Example: 0.5 kW power, 4 hours required
       "Appliance_40": {"power": .05, "hours": 4},    # Example: 0.5 kW power, 4 hours required# Example: 0.5 kW power, 4 hours required
}

# EV Charger details
ev_charge_required = 12  # kWh needed by end of day
ev_min_power = 0  # Minimum EV charging power (kW)
ev_max_power = 6.0  # Maximum EV charging power (kW)

# Target cost
target_cost = 1.0  # Example: Target total cost in $

# Initialize actual consumption data (simulation example)
actual_consumption = {t: 0 for t in time_slots}  # Initialize actual consumption per hour to zero


class TOU(EnergyModel):
    def __init__(self) -> None:
        self._actual_consumption = {}  # Real-time consumption data
        self._tou_rates = []  # TOU tariff rates
        self._thresholds = {} # Power thresholds for each hour
        self._observers = []  # List of observer objects
        self._appliances = {} # List of appliances
        self._differable_appliances={} # List of differeable appliances
        self._t=0
        self._appliance_vars = {}
        self._ev_power_vars={}
        self._power_thresholds={}
        self._ev_min_power=0
        self._ev_max_power=6.2
        self._ev_charge_required = 12  # kWh needed by end of day
        self._target_cost = 5.0 
        self._total_cost_expr=None

    def add_observer(self, observer) -> None:
        return super().add_observer(observer)
    
    def notify_observers(self) -> None:
        return super().notify_observers()
    
    def update_consumption(self) -> None:
        return super().update_consumption()
    
    def set_appliance(self,appliances)-> None:
        pass
    
    def set_differeable_appliances(self,appliances)-> None:
        pass
    

    def calculate_optimal_consumption(self,current_hour, actual_consumption):
        # Define the optimization problem
        self._problem = LpProblem("Dynamic_Optimization_for_Remaining_Hours", LpMinimize)
        
        # Remaining time slots
        remaining_time_slots = range(current_hour, 24)
        
        # Recalculate remaining target cost based on actual consumption so far
        total_actual_cost = sum(actual_consumption[t] * tou_rates[t] for t in range(current_hour))
        remaining_target_cost = target_cost - total_actual_cost
        # Calculate total accumulated kWh up to the current hour
        accumulated_kwh = sum(actual_consumption[t] for t in range(current_hour))

        # Print accumulated kWh
        print(f"Total accumulated kWh up to hour {current_hour}: {accumulated_kwh:.2f} kWh")
        print(f"Total accumulated cost up to hour {current_hour}: ${total_actual_cost:.2f}")

        # Define decision variables for appliances for remaining hours
        appliance_vars = {
            (appliance, t): LpVariable(f"{appliance}_t{t}", 0, 1, cat=LpBinary) 
            for appliance in appliances for t in remaining_time_slots
        }

        # Define continuous decision variables for EV charging power in each remaining time slot
        ev_power_vars = {t: LpVariable(f"EV_power_t{t}", ev_min_power, ev_max_power) for t in remaining_time_slots}

        # Define continuous decision variables for power threshold in each remaining time slot
        power_thresholds = {t: LpVariable(f"Power_Threshold_t{t}", 0, None, cat='Continuous') for t in remaining_time_slots}
        
        # Objective function: Minimize the sum of remaining power thresholds
        self._problem += lpSum(power_thresholds[t] for t in remaining_time_slots)

        # Constraints for appliances: Ensure each appliance runs for required hours
        for appliance in appliances:
            hours_run_so_far = sum(actual_consumption[t] >= appliances[appliance]["power"] for t in range(current_hour))
            remaining_hours_needed = appliances[appliance]["hours"] - hours_run_so_far
            self._problem += lpSum(appliance_vars[appliance, t] for t in remaining_time_slots) == remaining_hours_needed

        # Constraint for EV: Ensure it gets the required charge
        remaining_charge_needed = ev_charge_required - sum(actual_consumption[t] for t in range(current_hour) if "EV" in actual_consumption)
        self._problem += lpSum(ev_power_vars[t] for t in remaining_time_slots) >= remaining_charge_needed

        # Power capacity constraint: Total consumption should not exceed threshold
        for t in remaining_time_slots:
            self._problem += lpSum(appliances[appliance]["power"] * appliance_vars[appliance, t] for appliance in appliances) + \
                    ev_power_vars[t] <= power_thresholds[t]

        # Cost constraint: Total electricity cost should not exceed the remaining target cost
        total_cost_expr = lpSum(
            tou_rates[t] * (
                lpSum(appliances[appliance]["power"] * appliance_vars[appliance, t] for appliance in appliances) +
                ev_power_vars[t]
            ) for t in remaining_time_slots
        )
        self._problem += total_cost_expr <= remaining_target_cost

        # Solve the optimization problem
        self._problem.solve()
        solution_cost = value(total_cost_expr)


        # Print the results
        print(f"Optimal schedule to minimize max power threshold from hour {current_hour} onward:")
        for t in remaining_time_slots:
            appliance_schedule = [appliance for appliance in appliances if appliance_vars[appliance, t].value() == 1]
            ev_power = ev_power_vars[t].value()
            ev_schedule = f"EV Charging at {ev_power:.2f} kW" if ev_power > 0 else "EV Not Charging"
            print(f"Hour {t}: Appliances ON -> {appliance_schedule}, {ev_schedule}, Power Threshold: {power_thresholds[t].value():.2f} kW")
        
        # Print the total cost
        remaining_cost = value(total_cost_expr)
        print(f"Cost for the optimal solution from hour {current_hour} to the end: ${solution_cost:.2f}")
        print(f"Remaining Electricity Cost: ${remaining_cost:.2f}")



if __name__ == "__main__":
    # Simulate the system dynamically adjusting after each hour
    tou=TOU()
    for current_hour in time_slots:
        # Simulate random actual consumption exceeding the threshold in some hours
        actual_consumption[current_hour] = 2;min(10, max(0, 5 + (current_hour % 3 - 1) * 2))
        tou.calculate_optimal_consumption(current_hour, actual_consumption)
        # Recalculate remaining thresholds to achieve the target