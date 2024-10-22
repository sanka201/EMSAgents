import pulp

# Initial setup
battery_capacity = 45  # kWh
total_hours = 48  # 2 days of outage

# Variables: Power consumption per hour for each priority load (in kW)
P1 = 1.2  # kW for priority 1
P2 = 2.3  # kW for priority 2
P3 = 2.7  # kW for priority 3

# Function to optimize DOS based on remaining battery capacity
def optimize_dos(remaining_battery):
    problem = pulp.LpProblem("Energy_Management_Optimization", pulp.LpMaximize)

    # Variables: Duration of Service for each priority load (in hours)
    DOS1 = pulp.LpVariable('DOS1', lowBound=0, upBound=48, cat='Continuous')
    DOS2 = pulp.LpVariable('DOS2', lowBound=0, upBound=48, cat='Continuous')
    DOS3 = pulp.LpVariable('DOS3', lowBound=0, upBound=48, cat='Continuous')

    # Objective function
    problem += 3 * DOS1 + 2 * DOS2 + DOS3, "Maximize_Duration_of_Service"

    # Constraint: Total energy consumption cannot exceed the remaining battery capacity
    problem += P1 * DOS1 + P2 * DOS2 + P3 * DOS3 <= remaining_battery, "Battery_Capacity_Constraint"

    # Solve the problem
    problem.solve()

    # Return the DOS values
    return pulp.value(DOS1), pulp.value(DOS2), pulp.value(DOS3)

# Simulate hourly power usage over the entire outage period (48 hours)
hourly_usage = {
    # You can specify power usage for each hour here
    1: {'Priority 1': 1.2, 'Priority 2': 2.3, 'Priority 3': 2.7},  # Example: Priority 3 doesn't use power
    2: {'Priority 1': 1.2, 'Priority 2': 2.3, 'Priority 3': 2.7},  # Example: Priority 2 doesn't use power
    # Add more hourly usage data as needed, for all 48 hours
    # ... (hours 3 to 48)
}

# Initial optimization to determine DOS based on the entire battery capacity
DOS1_value, DOS2_value, DOS3_value = optimize_dos(battery_capacity)

# Initialize total DOS counters
total_DOS1 = 0
total_DOS2 = 0
total_DOS3 = 0

# Hourly simulation loop for 2 days (48 hours)
for hour in range(1, total_hours + 1):
    # Check if we have usage data for this hour; if not, assume no usage
    if hour in hourly_usage:
        used_power_p1 = hourly_usage[hour]['Priority 1']
        used_power_p2 = hourly_usage[hour]['Priority 2']
        used_power_p3 = hourly_usage[hour]['Priority 3']
    else:
        used_power_p1 = used_power_p2 = used_power_p3 = 0
    
    # Calculate total power used this hour
    total_power_used = used_power_p1 + used_power_p2 + used_power_p3
    
    # Deduct used power from battery capacity
    battery_capacity -= total_power_used

    # Re-optimize DOS based on remaining battery capacity
    DOS1_value, DOS2_value, DOS3_value = optimize_dos(battery_capacity)

    # Accumulate total DOS values based on actual usage
    total_DOS1 += 1 if used_power_p1 > 0 else 0
    total_DOS2 += 1 if used_power_p2 > 0 else 0
    total_DOS3 += 1 if used_power_p3 > 0 else 0

    # Output updated DOS values and battery capacity
    print(f"Hour {hour}:")
    print(f"Remaining Battery Capacity: {battery_capacity:.2f} kWh")
    print(f"Updated DOS for Priority 1 Load: {DOS1_value:.2f} hours")
    print(f"Updated DOS for Priority 2 Load: {DOS2_value:.2f} hours")
    print(f"Updated DOS for Priority 3 Load: {DOS3_value:.2f} hours")

    # Calculate the power thresholds for the next hour
    next_thresholds = {
        'Priority 1': P1 if DOS1_value > 0 else 0,
        'Priority 2': P2 if DOS2_value > 0 else 0,
        'Priority 3': P3 if DOS3_value > 0 else 0,
    }

    # Output the power thresholds for the next hour
    print(f"Next Hour Thresholds: Priority 1 = {next_thresholds['Priority 1']} kW, "
          f"Priority 2 = {next_thresholds['Priority 2']} kW, "
          f"Priority 3 = {next_thresholds['Priority 3']} kW\n")

# Output the total DOS values after 48 hours
print(f"Total DOS for Priority 1 Load: {total_DOS1} hours")
print(f"Total DOS for Priority 2 Load: {total_DOS2} hours")
print(f"Total DOS for Priority 3 Load: {total_DOS3} hours")
print(f"Total DOS Value: {total_DOS1 + total_DOS2 + total_DOS3} hours")
