import pulp

class BatteryOptimizer:
    def __init__(self, n_hours, battery_capacity, initial_soc, max_loads, weights, vip):
        """
        Initialize the optimizer with the necessary parameters.

        Parameters:
        - n_hours (int): Number of hours to optimize over in each step.
        - battery_capacity (float): Total capacity of the battery.
        - initial_soc (float): Initial SOC of the battery.
        - max_loads (dict): Maximum possible loads for each group.
        - weights (dict): Weights for each load group in the objective function.
        - vip: VOLTTRON VIP agent instance for RPC calls.
        """
        self.n_hours = n_hours
        self.battery_capacity = battery_capacity
        self.initial_soc = initial_soc
        self.max_loads = max_loads
        self.weights = weights
        self.M = battery_capacity  # Big M value
        self.vip = vip
        # Initialize SOC and other variables
        self.current_soc = initial_soc
        self.results = None

    def optimize(self):
        """
        Perform the battery optimization with gradual shedding.

        Returns:
        - dict: Results containing SOC and power supplied to each load group at each time step.
        """
        time_step = 0

        # Create the LP problem for the current time step
        prob = pulp.LpProblem(f"Battery_Optimization_Time_{time_step}", pulp.LpMaximize)

        # Decision Variables
        P_critical = {}
        P_medium = {}
        P_low = {}
        P_ev = {}
        SOC = {}
        Binary_Medium = {}
        Binary_Low = {}
        Binary_EV = {}

        # Initialize SOC at time 0 for this optimization step
        SOC[0] = self.current_soc
        #print("Current SOC Before:", self.vip.rpc.call('storageAgentagent-0.1_1', 'get_batter1_SOC').get(timeout=20))

        for t in range(1, self.n_hours + 1):
            # Power supplied to each load group at time t
            P_critical[t] = pulp.LpVariable(f'P_critical_{t}', lowBound=0, upBound=self.max_loads['critical'])
            P_medium[t] = pulp.LpVariable(f'P_medium_{t}', lowBound=0, upBound=self.max_loads['medium'])
            P_low[t] = pulp.LpVariable(f'P_low_{t}', lowBound=0, upBound=self.max_loads['low'])
            P_ev[t] = pulp.LpVariable(f'P_ev_{t}', lowBound=0, upBound=self.max_loads['ev'])

            # SOC variable at time t
            SOC[t] = pulp.LpVariable(f'SOC_{t}', lowBound=0, upBound=self.battery_capacity)

            # Binary variables for SOC thresholds
            Binary_Medium[t] = pulp.LpVariable(f'Binary_Medium_{t}', cat='Binary')
            Binary_Low[t] = pulp.LpVariable(f'Binary_Low_{t}', cat='Binary')
            Binary_EV[t] = pulp.LpVariable(f'Binary_EV_{t}', cat='Binary')

            # SOC balance equation
            total_power = P_critical[t] + P_medium[t] + P_low[t] + P_ev[t]
            prob += SOC[t] == SOC[t - 1] - total_power, f"SOC_balance_{t}"

            # Discharge rate constraints
            prob += total_power <= 0.2 * self.battery_capacity, f"Total_Discharge_Max_{t}"

            # SOC thresholds for each group
            SOC_threshold_upper_medium = 0.80 * self.battery_capacity
            SOC_threshold_lower_medium = 0.70 * self.battery_capacity

            SOC_threshold_upper_low = 0.70 * self.battery_capacity
            SOC_threshold_lower_low = 0.60 * self.battery_capacity

            SOC_threshold_upper_ev = 0.60 * self.battery_capacity
            SOC_threshold_lower_ev = 0.50 * self.battery_capacity

            # Critical load is always supplied fully unless SOC is critically low
            prob += P_critical[t] == self.max_loads['critical'], f"P_Critical_{t}"

            # Constraints linking SOC and Binary Variables
            # Medium
            prob += SOC[t] >= SOC_threshold_lower_medium - self.M * (1 - Binary_Medium[t]), f"SOC_Medium_Binary_Lower_{t}"
            prob += SOC[t] <= SOC_threshold_upper_medium + self.M * Binary_Medium[t], f"SOC_Medium_Binary_Upper_{t}"

            # Low
            prob += SOC[t] >= SOC_threshold_lower_low - self.M * (1 - Binary_Low[t]), f"SOC_Low_Binary_Lower_{t}"
            prob += SOC[t] <= SOC_threshold_upper_low + self.M * Binary_Low[t], f"SOC_Low_Binary_Upper_{t}"

            # EV
            prob += SOC[t] >= SOC_threshold_lower_ev - self.M * (1 - Binary_EV[t]), f"SOC_EV_Binary_Lower_{t}"
            prob += SOC[t] <= SOC_threshold_upper_ev + self.M * Binary_EV[t], f"SOC_EV_Binary_Upper_{t}"

            # Gradual shedding constraints
            # Medium
            slope_medium = self.max_loads['medium'] / (SOC_threshold_upper_medium - SOC_threshold_lower_medium)
            intercept_medium = -slope_medium * SOC_threshold_lower_medium

            prob += P_medium[t] >= 0, f"P_Medium_Lower_{t}"
            prob += P_medium[t] <= self.max_loads['medium'] * Binary_Medium[t], f"P_Medium_Upper_{t}"
            prob += P_medium[t] <= slope_medium * SOC[t] + intercept_medium + self.M * (1 - Binary_Medium[t]), f"P_Medium_SOC_{t}"

            # Low
            slope_low = self.max_loads['low'] / (SOC_threshold_upper_low - SOC_threshold_lower_low)
            intercept_low = -slope_low * SOC_threshold_lower_low

            prob += P_low[t] >= 0, f"P_Low_Lower_{t}"
            prob += P_low[t] <= self.max_loads['low'] * Binary_Low[t], f"P_Low_Upper_{t}"
            prob += P_low[t] <= slope_low * SOC[t] + intercept_low + self.M * (1 - Binary_Low[t]), f"P_Low_SOC_{t}"

            # EV
            slope_ev = self.max_loads['ev'] / (SOC_threshold_upper_ev - SOC_threshold_lower_ev)
            intercept_ev = -slope_ev * SOC_threshold_lower_ev

            prob += P_ev[t] >= 0, f"P_EV_Lower_{t}"
            prob += P_ev[t] <= self.max_loads['ev'] * Binary_EV[t], f"P_EV_Upper_{t}"
            prob += P_ev[t] <= slope_ev * SOC[t] + intercept_ev + self.M * (1 - Binary_EV[t]), f"P_EV_SOC_{t}"

            # Priority constraints
            prob += P_low[t] <= P_medium[t], f"Priority_Low_{t}"
            prob += P_ev[t] <= P_low[t], f"Priority_EV_{t}"

        # Objective function: maximize weighted sum of supplied loads
        total_weighted_load = pulp.lpSum([
            self.weights['critical'] * P_critical[t] +
            self.weights['medium'] * P_medium[t] +
            self.weights['low'] * P_low[t] +
            self.weights['ev'] * P_ev[t]
            for t in range(1, self.n_hours + 1)
        ])
        prob += total_weighted_load, "Total_Weighted_Load"

        # Solve the problem
        prob.solve()

        # Check if the problem is feasible
        if pulp.LpStatus[prob.status] != 'Optimal':
            print(f"Problem is infeasible at time step {time_step}")
            # Handle infeasibility as needed

        # Retrieve optimized power supplied for the first hour
        P_critical_value = pulp.value(P_critical[1])
        P_medium_value = pulp.value(P_medium[1])
        P_low_value = pulp.value(P_low[1])
        P_ev_value = pulp.value(P_ev[1])

        # Update current SOC (assuming consumption equals optimized power)
        total_consumption = P_critical_value + P_medium_value + P_low_value + P_ev_value
        self.current_soc = max(0, self.current_soc - total_consumption)
        print("Current SOC After:", self.current_soc)

        # Record results
        self.results = {
            'Time_Step': time_step,
            'Optimization_Status': pulp.LpStatus[prob.status],
            'P_critical_Optimized': P_critical_value,
            'P_medium_Optimized': P_medium_value,
            'P_low_Optimized': P_low_value,
            'P_ev_Optimized': P_ev_value,
            'SOC': self.current_soc
        }

        time_step += 1

        return self.results

# Example usage:
if __name__ == "__main__":
    n_hours = 1  # Number of hours to optimize ahead in each step
    battery_capacity = 100  # Total battery capacity in kWh
    initial_soc = 100       # Initial SOC in kWh

    # Maximum possible loads for each priority group in kW
    max_loads = {
        'critical': 2.5,
        'medium': 2,
        'low': 3,
        'ev': 6.02
    }

    # Weights for the objective function
    weights = {
        'critical': 100,
        'medium': 10,
        'low': 1,
        'ev': 0.1
    }

    # Initialize your VIP agent (assuming you have this set up)
    vip = None  # Replace with your actual VIP agent instance

    # Create an optimizer instance
    optimizer = BatteryOptimizer(n_hours, battery_capacity, initial_soc, max_loads, weights, vip)

    for i in range(5):
        # Perform optimization
        print(f"Optimization at time step {i}")
        results = optimizer.optimize()

        # Print the results
        print(f"Time Step: {results['Time_Step']}")
        print(f"Optimization Status: {results['Optimization_Status']}")
        print(f"Optimized Power for Critical Loads: {results['P_critical_Optimized']} kW")
        print(f"Optimized Power for Medium Loads: {results['P_medium_Optimized']} kW")
        print(f"Optimized Power for Low Loads: {results['P_low_Optimized']} kW")
        print(f"Optimized Power for EV Loads: {results['P_ev_Optimized']} kW")
        print(f"SOC: {results['SOC']} kWh")
        print("-" * 50)
