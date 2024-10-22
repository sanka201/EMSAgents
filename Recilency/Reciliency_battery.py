import pulp

# Define the problem
problem = pulp.LpProblem("Energy_Management_Optimization", pulp.LpMaximize)

# Variables: Duration of Service for each priority load (in hours)
DOS1 = pulp.LpVariable('DOS1', lowBound=0, upBound=48, cat='Continuous')
DOS2 = pulp.LpVariable('DOS2', lowBound=0, upBound=48, cat='Continuous')
DOS3 = pulp.LpVariable('DOS3', lowBound=0, upBound=48, cat='Continuous')

# Coefficients: Power consumption per hour for each priority load (in kW)
P1 = 6  # kW for priority 1
P2 = 5  # kW for priority 2
P3 = 3  # kW for priority 3

# Battery capacity (kWh)
battery_capacity = 45

# Objective function: Maximize the weighted sum of duration of service for higher priority loads
# We assign higher weights to higher priority loads.
problem += 3*DOS1 + 2*DOS2 + DOS3, "Maximize_Duration_of_Service"

# Constraint: Total energy consumption cannot exceed the battery capacity
problem += P1*DOS1 + P2*DOS2 + P3*DOS3 <= battery_capacity, "Battery_Capacity_Constraint"

# Solve the problem
problem.solve()

# Output the results
DOS1_value = pulp.value(DOS1)
DOS2_value = pulp.value(DOS2)
DOS3_value = pulp.value(DOS3)

print("Status:", pulp.LpStatus[problem.status])
print("Duration of Service for Priority 1 Load:", DOS1_value, "hours")
print("Duration of Service for Priority 2 Load:", DOS2_value, "hours")
print("Duration of Service for Priority 3 Load:", DOS3_value, "hours")
print("Total Energy Consumed:", P1*DOS1_value + P2*DOS2_value + P3*DOS3_value, "kWh")

# Defining thresholds in kW for each priority group for each hour of the day
hours_in_day = 24
priority_thresholds = {}

# Initialize the power thresholds for each priority group
for hour in range(1, hours_in_day + 1):
    priority_thresholds[hour] = {'Priority 1': 0, 'Priority 2': 0, 'Priority 3': 0}

# Calculate the power threshold for each hour for each priority group
for hour in range(1, hours_in_day + 1):
    if hour <= DOS1_value:
        priority_thresholds[hour]['Priority 1'] = P1  # Power for Priority 1
    if hour <= DOS2_value:
        priority_thresholds[hour]['Priority 2'] = P2  # Power for Priority 2
    if hour <= DOS3_value:
        priority_thresholds[hour]['Priority 3'] = P3  # Power for Priority 3

# Output the power thresholds for each priority group for each hour of the day
for hour, thresholds in priority_thresholds.items():
    print(f"Hour {hour}: Priority 1 = {thresholds['Priority 1']} kW, "
          f"Priority 2 = {thresholds['Priority 2']} kW, "
          f"Priority 3 = {thresholds['Priority 3']} kW")
