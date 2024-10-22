import pulp

# Define the number of days and hours in a day
days = range(1, 5)
hours = range(1, 25)  # 24 hours per day

# Initial battery capacity (in kWh)
battery_capacity = 90  # Example value

# Define the minimum battery reserve at the end of day 5 (10% of battery capacity)
min_battery_reserve = 0.1 * battery_capacity

# Initialize the problem
problem = pulp.LpProblem("MaximizeHourlyLoadSupport", pulp.LpMaximize)

# Decision variables for each priority load on each hour of each day (in kW)
p1 = pulp.LpVariable.dicts("p1", [(d, h) for d in days for h in hours], lowBound=0, upBound=.6, cat='Continuous')
p2 = pulp.LpVariable.dicts("p2", [(d, h) for d in days for h in hours], lowBound=0, upBound=.5, cat='Continuous')
p3 = pulp.LpVariable.dicts("p3", [(d, h) for d in days for h in hours], lowBound=0, upBound=.3, cat='Continuous')

# Remaining battery energy at the end of each day (in kWh)
r = pulp.LpVariable.dicts("r", days, lowBound=0, cat='Continuous')

# Objective function: Maximize energy usage in the early days
# Assign higher weights to earlier days to prioritize energy usage in the early days
problem += pulp.lpSum([(5 - d) * (p1[(d, h)] + p2[(d, h)] + p3[(d, h)]) for d in days for h in hours]), "MaximizeEarlyEnergyUsage"

# Initial condition: Battery at the start
problem += (r[1] == battery_capacity - pulp.lpSum([p1[(1, h)] + p2[(1, h)] + p3[(1, h)] for h in hours]), "InitialBatteryLevel")

# Battery dynamics for each subsequent day
for d in days:
    if d > 1:
        problem += (r[d] == r[d-1] - pulp.lpSum([p1[(d, h)] + p2[(d, h)] + p3[(d, h)] for h in hours]), f"BatteryDynamics_Day{d}")

# Ensure Priority 1 load is either fully supported or not at all
for d in days:
    for h in hours:
        problem += (p1[(d, h)] <= .6, f"CriticalLoadSupport_Day{d}_Hour{h}")
        problem += (p2[(d, h)] <= .5, f"Priority2_MaxLoad_Day{d}_Hour{h}")
        problem += (p3[(d, h)] <= .3, f"Priority3_MaxLoad_Day{d}_Hour{h}")

# Ensure battery reserve is at least 10% at the end of day 5
problem += (r[4] >= min_battery_reserve, "BatteryReserve_EndOfDay5")

# Solve the problem
problem.solve()

# Print the results
for d in days:
    print(f"Day {d}: Remaining Battery = {r[d].value()} kWh")
    for h in hours:
        print(f"  Hour {h}: Priority 1 = {p1[(d, h)].value()} kW, Priority 2 = {p2[(d, h)].value()} kW, Priority 3 = {p3[(d, h)].value()} kW")

print(f"Remaining Battery on Day 5: {r[4].value()} kWh")
