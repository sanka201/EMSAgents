import pulp

# Define the days of the outage (assumed to be 5 days)
days = range(1, 6)

# Initial battery capacity (in kWh)
battery_capacity = 70  # Example value

# Define the minimum battery reserve at the end of day 5 (10% of battery capacity)
min_battery_reserve = 0.1 * battery_capacity

# Initialize the problem
problem = pulp.LpProblem("MaximizeCriticalLoadResiliency", pulp.LpMaximize)

# Decision variables for each priority load on each day
x1 = pulp.LpVariable.dicts("x1", days, lowBound=0, upBound=6, cat='Continuous')
x2 = pulp.LpVariable.dicts("x2", days, lowBound=0, upBound=5, cat='Continuous')
x3 = pulp.LpVariable.dicts("x3", days, lowBound=0, upBound=3, cat='Continuous')

# Binary variables to indicate if Priority 1 is fully supported on a given day
y = pulp.LpVariable.dicts("y", days, cat='Binary')

# Remaining battery energy at the end of each day
r = pulp.LpVariable.dicts("r", days, lowBound=0, cat='Continuous')

# Objective function: Maximize the number of days Priority 1 load is fully supported
problem += pulp.lpSum([y[d] for d in days]), "MaximizePriority1SupportDays"

# Initial condition: Battery at the start
problem += (r[1] == battery_capacity - (x1[1] + x2[1] + x3[1]), "InitialBatteryLevel")

# Battery dynamics for each subsequent day
for d in days:
    if d > 1:
        problem += (r[d] == r[d-1] - (x1[d] + x2[d] + x3[d]), f"BatteryDynamics_Day{d}")

# Ensure Priority 1 load is either fully supported or not at all
for d in days:
    problem += (x1[d] == 6 * y[d], f"CriticalLoadSupport_Day{d}")

# Lower priority loads can be supported if there is enough energy
for d in days:
    problem += (x2[d] <= 5, f"Priority2_MaxLoad_Day{d}")
    problem += (x3[d] <= 3, f"Priority3_MaxLoad_Day{d}")

# Ensure battery reserve is at least 10% at the end of day 5
problem += (r[5] >= min_battery_reserve, "BatteryReserve_EndOfDay5")

# Solve the problem
problem.solve()

# Print the results
for d in days:
    print(f"Day {d}: Priority 1 = {x1[d].value()} kWh (Supported: {y[d].value()}), Priority 2 = {x2[d].value()} kWh, Priority 3 = {x3[d].value()} kWh, Remaining Battery = {r[d].value()} kWh")

print(f"Total Days Priority 1 Fully Supported: {pulp.value(problem.objective)} days")
print(f"Remaining Battery on Day 5: {r[5].value()} kWh")
