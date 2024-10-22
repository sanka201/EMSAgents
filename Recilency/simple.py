import pulp

# Define the days of the outage
days = range(1, 6)

# Available energy for each day (Battery + Solar + Wind)
E = {1: 20, 2: 15, 3: 10, 4: 3, 5: 4}  # Example values in kWh

# Weights for each priority level
w1 = 1  # Weight for Priority 1
w2 = 2  # Weight for Priority 2
w3 = 3  # Weight for Priority 3

# Initialize the problem
problem = pulp.LpProblem("EnergyManagementOptimization", pulp.LpMaximize)

# Decision variables for each priority load on each day
x1 = pulp.LpVariable.dicts("x1", days, lowBound=0, upBound=6, cat='Continuous')
x2 = pulp.LpVariable.dicts("x2", days, lowBound=0, upBound=5, cat='Continuous')
x3 = pulp.LpVariable.dicts("x3", days, lowBound=0, upBound=3, cat='Continuous')

# Objective function: Maximize the total weighted energy usage
problem += pulp.lpSum([w1 * x1[d] + w2 * x2[d] + w3 * x3[d] for d in days]), "MaximizeWeightedEnergyUsage"

# Constraints: Energy balance for each day
for d in days:
    problem += (x1[d] + x2[d] + x3[d] <= E[d], f"EnergyBalance_Day{d}")

# Solve the problem
problem.solve()

# Print the results
for d in days:
    print(f"Day {d}: Priority 1 = {x1[d].value()} kWh, Priority 2 = {x2[d].value()} kWh, Priority 3 = {x3[d].value()} kWh")

print(f"Total Optimized Value: {pulp.value(problem.objective)}")
