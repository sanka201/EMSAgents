
from Model.Optimizationstrategy import Optimizationstrategy
from pulp import LpMinimize, LpProblem, LpVariable, lpSum, LpBinary, value

class TOU(Optimizationstrategy):
    
    def optimize(self, model):
                # Define the optimization problem
        problem = LpProblem("Dynamic_Optimization_for_Remaining_Hours", LpMinimize)

        # Remaining time slots
        remaining_time_slots = range(model._current_hour, 24)

        # Recalculate remaining target cost based on actual consumption so far
        total_actual_cost = sum(model._actual_consumption[t] * model._tou_rates[t] for t in range(model._current_hour))
        remaining_target_cost = model._target_cost - total_actual_cost

        # Define decision variables for appliances for remaining hours
        appliance_vars = {
            (appliance, t): LpVariable(f"{appliance}_t{t}", 0, 1, cat=LpBinary)
            for appliance in model._appliances for t in remaining_time_slots
        }

        # Define continuous decision variables for EV charging power in each remaining time slot
        ev_power_vars = {t: LpVariable(f"EV_power_t{t}", model._ev_min_power, model._ev_max_power) for t in remaining_time_slots}

        # Define continuous decision variables for power threshold in each remaining time slot
        power_thresholds = {t: LpVariable(f"Power_Threshold_t{t}", 0, None, cat='Continuous') for t in remaining_time_slots}

        # Objective function: Minimize the sum of remaining power thresholds
        problem += lpSum(power_thresholds[t] for t in remaining_time_slots)

        # Constraints for appliances: Ensure each appliance runs for required hours
        for appliance in model._appliances:
            hours_run_so_far = sum(model._actual_consumption[t] >= model._appliances[appliance]["power"] for t in range(model._current_hour))
            remaining_hours_needed = model._appliances[appliance]["hours"] - hours_run_so_far
            problem += lpSum(appliance_vars[appliance, t] for t in remaining_time_slots) == remaining_hours_needed

        # Constraint for EV: Ensure it gets the required charge
        remaining_charge_needed = model._ev_charge_required - sum(model._actual_consumption[t] for t in range(model._current_hour))
        problem += lpSum(ev_power_vars[t] for t in remaining_time_slots) >= remaining_charge_needed

        # Power capacity constraint: Total consumption should not exceed threshold
        for t in remaining_time_slots:
            problem += lpSum(model._appliances[appliance]["power"] * appliance_vars[appliance, t] for appliance in model._appliances) + \
                       ev_power_vars[t] <= power_thresholds[t]

        # Cost constraint: Total electricity cost should not exceed the remaining target cost
        total_cost_expr = lpSum(
            model._tou_rates[t] * (
                lpSum(model._appliances[appliance]["power"] * appliance_vars[appliance, t] for appliance in model._appliances) +
                ev_power_vars[t]
            ) for t in remaining_time_slots
        )
        problem += total_cost_expr <= remaining_target_cost

        # Solve the optimization problem
        problem.solve()
        solution_cost = value(total_cost_expr)

        # Print the results
        print(f"Optimal schedule to minimize max power threshold from hour {model._current_hour} onward:")
        for t in remaining_time_slots:
            appliance_schedule = [appliance for appliance in model._appliances if appliance_vars[appliance, t].value() == 1]
            ev_power = ev_power_vars[t].value()
            ev_schedule = f"EV Charging at {ev_power:.2f} kW" if ev_power > 0 else "EV Not Charging"
            print(f"Hour {t}: Appliances ON -> {appliance_schedule}, {ev_schedule}, Power Threshold: {power_thresholds[t].value():.2f} kW")
        
        # Print the total cost
        remaining_cost = value(total_cost_expr)
        print(f"Cost for the optimal solution from hour {model._current_hour} to the end: ${solution_cost:.2f}")
        print(f"Remaining Electricity Cost: ${remaining_cost:.2f}")
        
        return [appliance_vars,ev_power_vars,power_thresholds]