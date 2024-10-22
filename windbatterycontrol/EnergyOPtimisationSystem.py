import pulp
from pulp import LpMaximize, LpProblem, LpVariable, LpStatus
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns

class EnergyOPtimisationSystem:
    def __init__(self, battery_capacity=8.0, battery_min_SOC=30, battery_max_SOC=100,
                 load_critical_max=2.8, load_medium_max=2.8, load_low_max=1.6, load_EV_max=6.5):
        """
        Initialize the Energy Management System with system parameters.
        """
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
        """
        if group == 'low':
            if SOC >= 85:
                return 0.0
            elif 75 <= SOC < 85:
                return (90 - SOC) / 10
            else:
                return 1.0
        elif group == 'medium':
            if SOC >= 80:
                return 0.0
            elif 65 <= SOC < 80:
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
        elif group == 'EV':

            if SOC > 95:
                return 0.0
            elif 70 <= SOC <= 95:
                return (85 - SOC) / 20
            else:
                return 1.0
        else:
            raise ValueError("Invalid priority group. Choose from 'low', 'medium', 'critical'.")

    def run_optimization(self, SOC_current, wind_power, EV_available=True, grid_failure=False, user_prefers_EV_over_critical=False):
        """
        Run the EMS optimization based on current SOC, wind power, and EV availability.
        """
        prob = LpProblem("Energy_Management_System", LpMaximize)
        
        # Remove EV load from low priority load
        load_low_total_max = self.load_low_max


        # Calculate shedding fractions
        shedding_low = self.calculate_shedding_fraction(SOC_current, 'low')
        shedding_medium = self.calculate_shedding_fraction(SOC_current, 'medium')
        shedding_critical = self.calculate_shedding_fraction(SOC_current, 'critical')
        shedding_EV = self.calculate_shedding_fraction(SOC_current, 'EV')

        # Adjust maximum served loads based on shedding
        load_low_served_max = load_low_total_max * (1 - shedding_low)
        load_medium_served_max = self.load_medium_max * (1 - shedding_medium)
        load_critical_served_max = self.load_critical_max * (1 - shedding_critical)
        load_EV_served_max = self.load_EV_max*(1-shedding_EV)
        

        # Define variables
        load_EV = LpVariable('Load_EV', 0, load_EV_served_max)
        load_critical = LpVariable('Load_Critical', 0, load_critical_served_max)
        load_medium = LpVariable('Load_Medium', 0, load_medium_served_max)
        load_low = LpVariable('Load_Low', 0, load_low_served_max)
        battery_charge = LpVariable('Battery_Charge', 0, wind_power)
        battery_discharge = LpVariable('Battery_Discharge', 0, self.battery_capacity)

        # Set weights based on SOC and user preference
        if SOC_current > 80 and user_prefers_EV_over_critical:
            w_EV = 100
            w_critical = 1000
            w_medium = 10
            w_low = 1
        else:
            w_critical = 1000
            w_medium = 100
            w_low = 10
            w_EV = 1  # EV has lowest priority or is not charged

        # Objective function with weights
        prob += (
            w_EV * load_EV + 
            w_critical * load_critical + 
            w_medium * load_medium + 
            w_low * load_low, 
            "Total_Served_Load"
        )

        # Power balance constraint
        prob += (
            wind_power + battery_discharge
            == load_EV + load_critical + load_medium + load_low + battery_charge,
            "Power_Balance"
        )

        # Ensure all wind power is used when SOC is high
        if SOC_current > 80 and wind_power>0:
            prob += (
                load_EV + load_critical + load_medium + load_low >= wind_power,
                "Use_All_Wind_Power"
            )

        # Battery SOC constraints
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

        # Prepare results
        result = {
            'Wind_Power_kW': round(wind_power, 2),
            'SOC_Current': round(SOC_current, 2),
            'EV_Available': EV_available,
            'Grid_Failure': grid_failure,
            'Status': LpStatus[prob.status],
            'Served_EV_Load_kW': round(load_EV.varValue, 2) if load_EV.varValue is not None else 0,
            'Served_Critical_Load_kW': round(load_critical.varValue, 2) if load_critical.varValue is not None else 0,
            'Served_Medium_Load_kW': round(load_medium.varValue, 2) if load_medium.varValue is not None else 0,
            'Served_Low_Load_kW': round(load_low.varValue, 2) if load_low.varValue is not None else 0,
            'Battery_Charge_kW': round(battery_charge.varValue, 2) if battery_charge.varValue is not None else 0,
            'Battery_Discharge_kW': round(battery_discharge.varValue, 2) if battery_discharge.varValue is not None else 0,
            'Battery_SOC_After_Operation_%': round(
                SOC_current + ((battery_charge.varValue - battery_discharge.varValue) / self.battery_capacity * 100),
                2
            ) if (battery_charge.varValue is not None and battery_discharge.varValue is not None) else SOC_current,
            'Shedding_Fraction_Low': round(shedding_low, 2),
            'Shedding_Fraction_EV' : round(shedding_EV,2),
            'Shedding_Fraction_Medium': round(shedding_medium, 2),
            'Shedding_Fraction_Critical': round(shedding_critical, 2),
            'Shed_Low_Priority': shedding_low > 0,
            'Shed_Medium_Priority': shedding_medium > 0,
            'Shed_Critical_Priority': shedding_critical > 0
        }

        self.results.append(result)


    def calculate_resilience_score(self):
        df = pd.DataFrame(self.results)
        df['CL_Compliance'] = df['Shedding_Fraction_Critical'] == 0
        df['CL_Compliance'] = df['CL_Compliance'].astype(int)
        df['ML_Efficiency'] = df['Served_Medium_Load_kW'] / self.load_medium_max
        df['LL_Efficiency'] = df['Served_Low_Load_kW'] / (self.load_low_max + self.load_EV_max)
        df['SOC_Maintenance'] = (df['Battery_SOC_After_Operation_%'] - self.battery_min_SOC) / (self.battery_max_SOC - self.battery_min_SOC)
        df['Resilience_Score'] = (df['CL_Compliance'] * 0.5) + \
                                  (df['ML_Efficiency'] * 0.2) + \
                                  (df['LL_Efficiency'] * 0.2) + \
                                  (df['SOC_Maintenance'] * 0.1)
        return df['Resilience_Score']

    def plot_results_with_matplotlib(self):
        df = pd.DataFrame(self.results)

        fig, axs = plt.subplots(3, 2, figsize=(18, 15))
        fig.suptitle('Energy Management System Results Across Scenarios', fontsize=18)

        # Plot served loads with islanded periods highlighted
        axs[0, 0].plot(df.index + 1, df['Served_Critical_Load_kW'], marker='o', label='Critical Load', color='red')
        axs[0, 0].plot(df.index + 1, df['Served_Medium_Load_kW'], marker='s', label='Medium Load', color='orange')
        axs[0, 0].plot(df.index + 1, df['Served_Low_Load_kW'], marker='^', label='Low Load', color='green')
        axs[0, 0].set_title('Served Loads Across Scenarios')
        axs[0, 0].set_xlabel('Scenario Index')
        axs[0, 0].set_ylabel('Served Load (kW)')
        axs[0, 0].legend()
        axs[0, 0].grid(True)

        # Highlight the islanded (grid failure) periods in the background
        for idx, grid_fail in enumerate(df['Grid_Failure']):
            if grid_fail:
                axs[0, 0].axvspan(idx + 0.5, idx + 1.5, facecolor='grey', alpha=0.3)

        # Plot battery SOC with islanded periods highlighted
        axs[0, 1].plot(df.index + 1, df['Battery_SOC_After_Operation_%'], marker='o', color='blue')
        axs[0, 1].set_title('Battery SOC After Operations')
        axs[0, 1].set_xlabel('Scenario Index')
        axs[0, 1].set_ylabel('Battery SOC (%)')
        axs[0, 1].grid(True)

        for idx, grid_fail in enumerate(df['Grid_Failure']):
            if grid_fail:
                axs[0, 1].axvspan(idx + 0.5, idx + 1.5, facecolor='grey', alpha=0.3)

        # Plot battery charge and discharge with islanded periods highlighted
        axs[1, 0].plot(df.index + 1, df['Battery_Charge_kW'], marker='o', label='Charge', color='green')
        axs[1, 0].plot(df.index + 1, df['Battery_Discharge_kW'], marker='s', label='Discharge', color='red')
        axs[1, 0].set_title('Battery Charge and Discharge Across Scenarios')
        axs[1, 0].set_xlabel('Scenario Index')
        axs[1, 0].set_ylabel('Power (kW)')
        axs[1, 0].legend()
        axs[1, 0].grid(True)

        for idx, grid_fail in enumerate(df['Grid_Failure']):
            if grid_fail:
                axs[1, 0].axvspan(idx + 0.5, idx + 1.5, facecolor='grey', alpha=0.3)

        # Plot wind power as bar chart with islanded periods highlighted
        axs[1, 1].bar(df.index + 1, df['Wind_Power_kW'], color='purple')
        axs[1, 1].set_title('Wind Power Across Scenarios')
        axs[1, 1].set_xlabel('Scenario Index')
        axs[1, 1].set_ylabel('Wind Power (kW)')
        axs[1, 1].grid(True)

        for idx, grid_fail in enumerate(df['Grid_Failure']):
            if grid_fail:
                axs[1, 1].axvspan(idx + 0.5, idx + 1.5, facecolor='grey', alpha=0.3)

        # Plot shedding fractions with islanded periods highlighted
        axs[2, 0].plot(df.index + 1, df['Shedding_Fraction_Critical'], marker='o', label='Critical Shedding', color='red')
        axs[2, 0].plot(df.index + 1, df['Shedding_Fraction_Medium'], marker='s', label='Medium Shedding', color='orange')
        axs[2, 0].plot(df.index + 1, df['Shedding_Fraction_Low'], marker='^', label='Low Shedding', color='green')
        axs[2, 0].set_title('Shedding Fractions Across Scenarios')
        axs[2, 0].set_xlabel('Scenario Index')
        axs[2, 0].set_ylabel('Shedding Fraction')
        axs[2, 0].legend()
        axs[2, 0].grid(True)

        for idx, grid_fail in enumerate(df['Grid_Failure']):
            if grid_fail:
                axs[2, 0].axvspan(idx + 0.5, idx + 1.5, facecolor='grey', alpha=0.3)

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.show()

    def plot_resiliency_matrix(self):
        df = pd.DataFrame(self.results)
        resilience_scores = self.calculate_resilience_score()
        df['Resilience_Score'] = resilience_scores

        plt.figure(figsize=(10, 8))
        sns.heatmap(
            df.pivot_table(values='Resilience_Score', index='Wind_Power_kW', columns=df.index + 1, fill_value=0),
            annot=True, cmap='viridis', cbar_kws={'label': 'Resilience Score'}
        )
        plt.title('Resiliency Matrix: Wind Power vs Scenario Index')
        plt.xlabel('Scenario Index')
        plt.ylabel('Wind Power (kW)')
        plt.show()



def main():
# Instantiate EMS and simulate scenarios with grid failures and islanding mode
    ems = EnergyOPtimisationSystem()

    # Define simulation parameters
    initial_SOC = 100.0  # Starting with a fully charged battery
    num_scenarios = 10    # Total number of scenarios to simulate
    grid_failure_scenarios = [False, False, True, True, False, False, False, True, True, False]  # Grid failure scenarios
    ev_availability = np.random.choice([True, False], size=num_scenarios, p=[0.7, 0.3])

    # Generate varying wind power levels (e.g., fluctuating between 0 and 10 kW)
    time_steps = np.arange(1, num_scenarios + 1)
    wind_power_levels = 5 + 5 * np.sin(2 * np.pi * time_steps / num_scenarios)  # Wind power between 0 and 10 kW
    wind_power_levels += np.random.normal(0, 1, num_scenarios)
    wind_power_levels = np.clip(wind_power_levels, 0, None)  # Ensure wind power is non-negative

    # Initialize SOC
    current_SOC = initial_SOC

    # Run the simulation for the defined scenarios
    for idx in range(num_scenarios):
        wind = wind_power_levels[idx]
        ev = ev_availability[idx]
        grid_failure = grid_failure_scenarios[idx]
        print(f"--- Scenario {idx+1}: SOC={current_SOC}% | Wind Power={wind:.2f} kW | EV Available={ev} | Grid Failure: {grid_failure} ---")
        ems.run_optimization(SOC_current=current_SOC, wind_power=wind, EV_available=ev, grid_failure=grid_failure)
        current_SOC = ems.results[-1]['Battery_SOC_After_Operation_%']

# Plot all results using Matplotlib
#ems.plot_results_with_matplotlib()

# Plot the resiliency matrix separately
#ems.plot_resiliency_matrix()
if __name__ == "__main__":
    main()


