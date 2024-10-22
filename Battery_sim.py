import numpy as np
import matplotlib.pyplot as plt

class Battery:
    def __init__(self, capacity_kWh, max_discharge_kW, voltage_nominal, internal_resistance, initial_soc=1.0):
        self.capacity_kWh = capacity_kWh                  # Total capacity in kWh
        self.capacity_Wh = capacity_kWh * 1000            # Total capacity in Wh
        self.max_discharge_kW = max_discharge_kW          # Max discharge power in kW
        self.voltage_nominal = voltage_nominal            # Nominal voltage in Volts
        self.internal_resistance = internal_resistance    # Internal resistance in Ohms
        self.soc = initial_soc * self.capacity_Wh         # State of Charge in Wh

    def discharge(self, power_demand_W, duration_h):
        # Convert power demand to current demand
        current_demand = power_demand_W / self.get_voltage()

        # Adjust current demand considering max discharge current
        max_current = self.max_discharge_kW * 1000 / self.voltage_nominal
        actual_current = min(current_demand, max_current)

        # Update voltage based on internal resistance
        terminal_voltage = self.get_voltage() - actual_current * self.internal_resistance

        # Calculate actual power supplied
        actual_power = terminal_voltage * actual_current

        # Energy drawn from battery
        energy_drawn_Wh = actual_power * duration_h

        # Update State of Charge
        self.soc -= energy_drawn_Wh

        # Prevent SOC from dropping below zero
        if self.soc < 0:
            energy_drawn_Wh += self.soc  # Adjust energy drawn
            self.soc = 0

        return actual_power  # Actual power supplied in Watts

    def get_voltage(self):
        # Simplified voltage model: voltage drops linearly with SOC
        min_voltage = self.voltage_nominal * 0.9
        voltage = min_voltage + (self.soc / self.capacity_Wh) * (self.voltage_nominal - min_voltage)
        return voltage

    def get_soc_percent(self):
        # Return State of Charge as a percentage
        return (self.soc / self.capacity_Wh) * 100

class Load:
    def __init__(self, max_power_kW):
        self.max_power_kW = max_power_kW

    def get_power(self, time):
        # For simplicity, assume constant load; modify if variable load is needed
        return self.max_power_kW * 1000  # Convert kW to W

def simulate_blackout(battery1, battery2, load1, load2, grid_status_func, time_steps):
    duration_h = 1  # Duration of each time step in hours
    soc1_history = []
    soc2_history = []
    grid_status_history = []
    time_axis = []

    for t in range(time_steps):
        grid_available = grid_status_func(t)
        grid_status_history.append(grid_available)
        power_load1 = load1.get_power(t)
        power_load2 = load2.get_power(t)

        if grid_available:
            # Grid supplies loads; batteries remain at current SOC
            print(f"Time {t}: Grid is up. Loads are supplied by the grid.")
        else:
            # Grid is down; batteries supply loads
            power_from_battery1 = battery1.discharge(power_load1, duration_h)
            power_from_battery2 = battery2.discharge(power_load2, duration_h)

            # Check if batteries can meet the loads fully
            if power_from_battery1 < power_load1:
                load_shed1 = (power_load1 - power_from_battery1) / 1000  # Convert W to kW
                print(f"Time {t}: Battery 1 cannot fully supply Load 1. Load shed of {load_shed1:.2f} kW.")
            if power_from_battery2 < power_load2:
                load_shed2 = (power_load2 - power_from_battery2) / 1000  # Convert W to kW
                print(f"Time {t}: Battery 2 cannot fully supply Load 2. Load shed of {load_shed2:.2f} kW.")
            else:
                print(f"Time {t}: Batteries are supplying the loads during blackout.")

        soc1_history.append(battery1.get_soc_percent())
        soc2_history.append(battery2.get_soc_percent())
        time_axis.append(t)

    # Plot State of Charge over time
    plt.figure(figsize=(12, 6))
    plt.plot(time_axis, soc1_history, label='Battery 1 SoC (%)')
    plt.plot(time_axis, soc2_history, label='Battery 2 SoC (%)')
    plt.xlabel('Time Steps (Hours)')
    plt.ylabel('State of Charge (%)')
    plt.title('Battery State of Charge Over Time')
    plt.legend()
    plt.grid(True)
    plt.show()

def grid_status(t):
    # Define when the grid is up or down
    blackout_start = 5  # Time step when blackout starts
    if t >= blackout_start:
        return False  # Grid is down
    else:
        return True   # Grid is up

# Initialize Batteries with dynamic equations
battery1 = Battery(
    capacity_kWh=100,             # Battery capacity in kWh
    max_discharge_kW=10,          # Max discharge power in kW
    voltage_nominal=400,          # Nominal voltage in Volts
    internal_resistance=0.05,     # Internal resistance in Ohms
    initial_soc=1.0               # Initial State of Charge (100%)
)

battery2 = Battery(
    capacity_kWh=500,             # Battery capacity in kWh
    max_discharge_kW=150,         # Max discharge power in kW
    voltage_nominal=800,          # Nominal voltage in Volts
    internal_resistance=0.02,     # Internal resistance in Ohms
    initial_soc=1.0               # Initial State of Charge (100%)
)

# Initialize Loads
load1 = Load(max_power_kW=10)    # Load with maximum of 10 kW
load2 = Load(max_power_kW=150)   # Load with maximum of 150 kW

# Run Simulation
simulate_blackout(battery1, battery2, load1, load2, grid_status_func=grid_status, time_steps=12)
