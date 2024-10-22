import pulp

# Initialize the problem
prob = pulp.LpProblem("Wind_Battery_Optimal_Load_Increase", pulp.LpMaximize)

# Parameters
P_wind = 2  # Wind turbine output in kW
SOC_max = 45  # Battery capacity in kWh
SOC_initial = 25  # Initial SOC in kWh (battery fully charged)
eta_battery = 0.95  # Battery efficiency
delta_t = 1  # Time step in hours
P_battery_max = 10  # Battery max charge/discharge rate in kW
delta = 0.1  # Small positive value to ensure battery discharge

# Load capacities (kW)
P_load_min = {
    'critical': 1.0,  # Minimum required power for critical load
    'medium': 0.5,
    'low': 0.0,
}

P_load_max = {
    'critical': 1.7,
    'medium': 2.6,
    'low': 3.2,
}

# EV load capacities (kW)
P_ev_min = 0.0
P_ev_max = 6.2

# Weights for the objective function
weights = {
    'critical': 100,
    'medium': 10,
    'low': 1,
}

# Penalties and costs
penalty_curtail = 100  # Adjusted penalty for curtailment
cost_ev = 1  # Small cost per kW for supplying EV load

# EV availability parameter (1 if available, 0 if not)
EV_available = 1  # Change to 0 if EV is not available

# Decision Variables
P_load = {}
for load in P_load_max.keys():
    P_load[load] = pulp.LpVariable(
        f"P_{load}", lowBound=P_load_min[load], upBound=P_load_max[load]
    )

P_ev = pulp.LpVariable(
    "P_ev", lowBound=P_ev_min, upBound=P_ev_max * EV_available
)

P_curtail = pulp.LpVariable("P_curtail", lowBound=0)
P_battery = pulp.LpVariable("P_battery", lowBound=-P_battery_max, upBound=P_battery_max)
SOC = pulp.LpVariable("SOC", lowBound=0, upBound=SOC_max)

# Objective Function
prob += (
    pulp.lpSum([weights[load] * P_load[load] for load in P_load.keys()]) -
    penalty_curtail * P_curtail -
    cost_ev * P_ev
), "Total_Weighted_Load"

# Constraints

# a. Power Balance Constraint
prob += (
    pulp.lpSum([P_load[load] for load in P_load.keys()]) + P_ev ==
    P_wind + P_battery - P_curtail
), "Power_Balance"

# b. Battery Charging Constraint
prob += P_battery >= -(P_wind - pulp.lpSum([P_load[load] for load in P_load.keys()]) - P_ev + P_curtail), "Battery_Charging"

# c. Battery SOC Update
prob += SOC == SOC_initial - (P_battery * delta_t) / eta_battery, "SOC_Update"

# d. Battery SOC Limits
# Already enforced by variable bounds

# e. Battery Charge/Discharge Rate Limits
# Already enforced by variable bounds

# f. Load Adjustment to Exceed Wind Power
prob += (
    pulp.lpSum([P_load[load] for load in P_load.keys()]) + P_ev >= P_wind + delta
), "Load_Exceeds_Wind"

# Solve the problem
prob.solve()

# Print the results
print(f"Status: {pulp.LpStatus[prob.status]}")
print(f"Objective Function Value: {pulp.value(prob.objective)}")
print(f"Battery Power (Positive=Discharging, Negative=Charging): {P_battery.varValue:.2f} kW")
print(f"Battery SOC: {SOC.varValue:.2f} kWh")
print(f"Curtailed Wind Power: {P_curtail.varValue:.2f} kW")
print(f"Power supplied to EV load: {P_ev.varValue:.2f} kW")

for load in P_load.keys():
    print(f"Power supplied to {load} load: {P_load[load].varValue:.2f} kW")
