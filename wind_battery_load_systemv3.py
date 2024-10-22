import pulp
from pulp import LpMaximize, LpProblem, LpVariable, LpStatus, value
import matplotlib.pyplot as plt
import pandas as pd

class EnergyManagementSystem:
    def __init__(self, wind_power=10.0, battery_capacity=45.0, battery_min_SOC=20, battery_max_SOC=100,
                 load_critical_max=1.9, load_medium_max=3.3, load_low_max=2.9, load_EV_max=6.02):
        """
        Initialize the Energy Management System with system parameters.

        Parameters:
        - wind_power (float): Maximum wind power generation in kW.
        - battery_capacity (float): Battery capacity in kWh.
        - battery_min_SOC (float): Minimum State of Charge (%) for the battery.
        - battery_max_SOC (float): Maximum State of Charge (%) for the battery.
        - load_critical_max (float): Maximum critical load in kW.
        - load_medium_max (float): Maximum medium priority load in kW.
        - load_low_max (float): Maximum low priority load in kW.
        - load_EV_max (float): Maximum EV load in kW.
        """
        self.wind_power = wind_power
        self.battery_capacity = battery_capacity
        self.battery_min_SOC = battery_min_SOC
        self.battery_max_SOC = battery_max_SOC
        self.load_critical_max = load_critical_max
        self.load_medium_max = load_medium_max
        self.load_low_max = load_low_max
        self.load_EV_max = load_EV_max
        # Initialize results list
        self.results = []

    def calculate_shedding_fraction(self, SOC, group):
        """
        Calculate the shedding fraction for a given priority group based on SOC.

        Parameters:
        - SOC (float): Current State of Charge (%) of the battery.
        - group (str): Priority group ('low', 'medium', 'critical').

        Returns:
        - float: Shedding fraction (0 to 1).
        """
        if group == 'low':
            if SOC >= 90:
                return 0.0
            elif 80 <= SOC < 90:
                return (90 - SOC) / 10
            else:
                return 1.0
        elif group == 'medium':
            if SOC >= 80:
                return 0.0
            elif 70 <= SOC < 80:
                return (80 - SOC) / 10
            else:
                return 1.0
        elif group == 'critical':
            if SOC > 40:
                return 0.0
            elif 20 <= SOC <= 40:
                return (40 - SOC) / 20
            else:
                return 1.0
        else:
            raise ValueError("Invalid priority group. Choose from 'low', 'medium', 'critical'.")

    def run_optimization(self, SOC_current, EV_available=True):
        """
        Run the EMS optimization based on current SOC and EV availability.

        Parameters:
        - SOC_current (float): Current State of Charge (%) of the battery.
        - EV_available (bool): Whether the EV is available for charging.
        """
        # Initialize the optimization problem
        prob = LpProblem("Energy_Management_System", LpMaximize)

        # Adjust low priority load if EV is available
        load_low_total_max = self.load_low_max + (self.load_EV_max if EV_available else 0)

        # Calculate shedding fractions
        shedding_low = self.calculate_shedding_fraction(SOC_current, 'low')
        shedding_medium = self.calculate_shedding_fraction(SOC_current, 'medium')
        shedding_critical = self.calculate_shedding_fraction(SOC_current, 'critical')

        # Calculate served load maximums based on shedding fractions
        load_low_served_max = load_low_total_max * (1 - shedding_low)
        load_medium_served_max = self.load_medium_max * (1 - shedding_medium)
        load_critical_served_max = self.load_critical_max * (1 - shedding_critical)

        # Decision Variables
        # Load consumptions
        load_critical = LpVariable('Load_Critical', 0, load_critical_served_max)
        load_medium = LpVariable('Load_Medium', 0, load_medium_served_max)
        load_low = LpVariable('Load_Low', 0, load_low_served_max)

        # Battery operations
        battery_charge = LpVariable('Battery_Charge', 0, self.wind_power)  # Charging limited by wind power
        battery_discharge = LpVariable('Battery_Discharge', 0, self.battery_capacity)  # Discharging limited by battery capacity

        # Objective: Maximize the total served load
        prob += load_critical + load_medium + load_low, "Total_Served_Load"

        # Power Balance Constraint
        prob += (
            self.wind_power + battery_discharge 
            == load_critical + load_medium + load_low + battery_charge,
            "Power_Balance"
        )

        # SOC Constraints
        # Ensure SOC remains within [battery_min_SOC, battery_max_SOC] after operations
        prob += (
            SOC_current + (battery_charge - battery_discharge) / self.battery_capacity * 100 
            >= self.battery_min_SOC, 
            "SOC_Min"
        )
        prob += (
            SOC_current + (battery_charge - battery_discharge) / self.battery_capacity * 100 
            <= self.battery_max_SOC, 
            "SOC_Max"
        )

        # Solve the optimization problem
        prob.solve()

        # Store the results
        result = {
            'SOC_Current': SOC_current,
            'EV_Available': EV_available,
            'Status': LpStatus[prob.status],
            'Served_Critical_Load_kW': round(load_critical.varValue, 2) if load_critical.varValue is not None else 0,
            'Served_Medium_Load_kW': round(load_medium.varValue, 2) if load_medium.varValue is not None else 0,
            'Served_Low_Load_kW': round(load_low.varValue, 2) if load_low.varValue is not None else 0,
            'Battery_Charge_kW': round(battery_charge.varValue, 2) if battery_charge.varValue is not None else 0,
            'Battery_Discharge_kW': round(battery_discharge.varValue, 2) if battery_discharge.varValue is not None else 0,
            'Battery_SOC_After_Operation_%': round(
                SOC_current + ( (battery_charge.varValue - battery_discharge.varValue) / self.battery_capacity * 100),
                2
            ) if (battery_charge.varValue is not None and battery_discharge.varValue is not None) else SOC_current,
            'Shedding_Fraction_Low': round(shedding_low, 2),
            'Shedding_Fraction_Medium': round(shedding_medium, 2),
            'Shedding_Fraction_Critical': round(shedding_critical, 2),
            'Shed_Low_Priority': shedding_low > 0,
            'Shed_Medium_Priority': shedding_medium > 0,
            'Shed_Critical_Priority': shedding_critical > 0
        }

        self.results.append(result)

    def print_results(self):
        """
        Print the latest optimization results.
        """
        if not self.results:
            print("No results available. Please run the optimization first.")
            return
        latest_result = self.results[-1]
        print("=== Energy Management System Results ===")
        print(f"Status: {latest_result['Status']}")
        print(f"Served Critical Load: {latest_result['Served_Critical_Load_kW']} kW")
        print(f"Served Medium Load: {latest_result['Served_Medium_Load_kW']} kW")
        print(f"Served Low Load: {latest_result['Served_Low_Load_kW']} kW")
        print(f"Battery Charge: {latest_result['Battery_Charge_kW']} kW")
        print(f"Battery Discharge: {latest_result['Battery_Discharge_kW']} kW")
        print(f"Battery SOC After Operation: {latest_result['Battery_SOC_After_Operation_%']}%")
        print(f"Shedding Fraction - Low Priority: {latest_result['Shedding_Fraction_Low'] * 100}%")
        print(f"Shedding Fraction - Medium Priority: {latest_result['Shedding_Fraction_Medium'] * 100}%")
        print(f"Shedding Fraction - Critical Priority: {latest_result['Shedding_Fraction_Critical'] * 100}%")
        print(f"Shed Low Priority: {'Yes' if latest_result['Shed_Low_Priority'] else 'No'}")
        print(f"Shed Medium Priority: {'Yes' if latest_result['Shed_Medium_Priority'] else 'No'}")
        print(f"Shed Critical Priority: {'Yes' if latest_result['Shed_Critical_Priority'] else 'No'}")
        print("========================================\n")

    def get_results(self):
        """
        Retrieve all optimization results.

        Returns:
        - list of dict: A list containing dictionaries of optimization results.
        """
        return self.results.copy()

    def reset_results(self):
        """
        Reset the stored results.
        """
        self.results = []

    def plot_latest_results(self):
        """
        Plot the latest optimization results using Matplotlib.
        """
        if not self.results:
            print("No results available to plot. Please run the optimization first.")
            return
        latest_result = self.results[-1]

        # Prepare data for plotting
        load_categories = ['Critical', 'Medium', 'Low']
        served_loads = [
            latest_result['Served_Critical_Load_kW'],
            latest_result['Served_Medium_Load_kW'],
            latest_result['Served_Low_Load_kW']
        ]

        shedding_fractions = [
            latest_result['Shedding_Fraction_Critical'],
            latest_result['Shedding_Fraction_Medium'],
            latest_result['Shedding_Fraction_Low']
        ]

        # Create subplots
        fig, axs = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Energy Management System Visualization', fontsize=16)

        # Served Loads Bar Chart
        axs[0, 0].bar(load_categories, served_loads, color=['red', 'orange', 'green'])
        axs[0, 0].set_title('Served Loads by Priority Category')
        axs[0, 0].set_ylabel('Served Load (kW)')
        for i, v in enumerate(served_loads):
            axs[0, 0].text(i, v + 0.05, f"{v:.2f}", ha='center')

        # Shedding Fractions Pie Chart or No Shedding Indicator
        total_shedding = sum(shedding_fractions)
        if total_shedding > 0:
            axs[0, 1].pie(
                [f * 100 for f in shedding_fractions],
                labels=load_categories,
                autopct='%1.1f%%',
                startangle=140,
                colors=['lightcoral', 'gold', 'lightgreen']
            )
            axs[0, 1].set_title('Shedding Fractions by Priority Category')
        else:
            axs[0, 1].text(0.5, 0.5, 'No Shedding Occurred', horizontalalignment='center',
                           verticalalignment='center', fontsize=12, color='blue')
            axs[0, 1].axis('off')
            axs[0, 1].set_title('Shedding Fractions by Priority Category')

        # Battery SOC Gauge (Simulated using a horizontal bar)
        axs[1, 0].barh(['Battery SOC'], [latest_result['Battery_SOC_After_Operation_%']], color='skyblue')
        axs[1, 0].set_xlim(0, 100)
        axs[1, 0].set_xlabel('State of Charge (%)')
        axs[1, 0].set_title('Battery SOC After Operation')
        axs[1, 0].text(
            latest_result['Battery_SOC_After_Operation_%'] + 1, 0,
            f"{latest_result['Battery_SOC_After_Operation_%']}%",
            va='center'
        )
        # Add threshold lines
        axs[1, 0].axvline(x=40, color='gray', linestyle='--', linewidth=1)
        axs[1, 0].axvline(x=20, color='red', linestyle='--', linewidth=1)
        axs[1, 0].text(42, 0, '40%', va='center', fontsize=8, color='gray')
        axs[1, 0].text(22, 0, '20%', va='center', fontsize=8, color='red')

        # Battery Charge and Discharge Bar Chart
        battery_ops = ['Charge', 'Discharge']
        battery_values = [
            latest_result['Battery_Charge_kW'],
            latest_result['Battery_Discharge_kW']
        ]
        axs[1, 1].bar(battery_ops, battery_values, color=['green', 'red'])
        axs[1, 1].set_title('Battery Charge and Discharge')
        axs[1, 1].set_ylabel('Power (kW)')
        for i, v in enumerate(battery_values):
            axs[1, 1].text(i, v + 0.05, f"{v:.2f}", ha='center')

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.show()

    def plot_all_results(self):
        """
        Plot all optimization results using Matplotlib.
        """
        if not self.results:
            print("No results available to plot. Please run the optimization first.")
            return

        # Create a DataFrame from results
        df = pd.DataFrame(self.results)

        # Set up the figure and subplots
        fig, axs = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Energy Management System Comprehensive Visualization', fontsize=18)

        # Served Loads Across SOC Levels
        axs[0, 0].plot(df['SOC_Current'], df['Served_Critical_Load_kW'], marker='o', label='Critical Load')
        axs[0, 0].plot(df['SOC_Current'], df['Served_Medium_Load_kW'], marker='s', label='Medium Load')
        axs[0, 0].plot(df['SOC_Current'], df['Served_Low_Load_kW'], marker='^', label='Low Load')
        axs[0, 0].set_title('Served Loads Across SOC Levels')
        axs[0, 0].set_xlabel('SOC (%)')
        axs[0, 0].set_ylabel('Served Load (kW)')
        axs[0, 0].legend()
        axs[0, 0].grid(True)

        # Shedding Fractions Across SOC Levels
        axs[0, 1].plot(df['SOC_Current'], df['Shedding_Fraction_Critical'], marker='o', label='Critical Shedding')
        axs[0, 1].plot(df['SOC_Current'], df['Shedding_Fraction_Medium'], marker='s', label='Medium Shedding')
        axs[0, 1].plot(df['SOC_Current'], df['Shedding_Fraction_Low'], marker='^', label='Low Shedding')
        axs[0, 1].set_title('Shedding Fractions Across SOC Levels')
        axs[0, 1].set_xlabel('SOC (%)')
        axs[0, 1].set_ylabel('Shedding Fraction')
        axs[0, 1].legend()
        axs[0, 1].grid(True)

        # Battery SOC After Operations
        axs[1, 0].plot(df['SOC_Current'], df['Battery_SOC_After_Operation_%'], marker='o', color='purple')
        axs[1, 0].set_title('Battery SOC After Operations Across SOC Levels')
        axs[1, 0].set_xlabel('SOC (%)')
        axs[1, 0].set_ylabel('Battery SOC After Operation (%)')
        axs[1, 0].grid(True)
        axs[1, 0].axhline(y=40, color='gray', linestyle='--', linewidth=1)
        axs[1, 0].axhline(y=20, color='red', linestyle='--', linewidth=1)
        axs[1, 0].text(5, 42, '40%', va='center', fontsize=8, color='gray')
        axs[1, 0].text(5, 22, '20%', va='center', fontsize=8, color='red')

        # Battery Charge and Discharge Across SOC Levels
        axs[1, 1].plot(df['SOC_Current'], df['Battery_Charge_kW'], marker='o', label='Battery Charge', color='green')
        axs[1, 1].plot(df['SOC_Current'], df['Battery_Discharge_kW'], marker='s', label='Battery Discharge', color='red')
        axs[1, 1].set_title('Battery Charge and Discharge Across SOC Levels')
        axs[1, 1].set_xlabel('SOC (%)')
        axs[1, 1].set_ylabel('Power (kW)')
        axs[1, 1].legend()
        axs[1, 1].grid(True)

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.show()

# Instantiate the EMS with default parameters
ems = EnergyManagementSystem()

# Define different SOC scenarios to test EMS behavior
soc_levels = [95, 85, 75, 35, 15]  # SOC percentages
ev_availability = [True, True, True, False, False]  # EV availability corresponding to SOC levels

# Iterate through each scenario, run the optimization, and plot the latest results
for soc, ev in zip(soc_levels, ev_availability):
    print(f"--- Running EMS for SOC: {soc}% | EV Available: {ev} ---")
    ems.run_optimization(SOC_current=soc, EV_available=ev)
    ems.print_results()
    ems.plot_latest_results()

# After running multiple scenarios, visualize all results together
ems.plot_all_results()
