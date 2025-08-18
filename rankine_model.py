from tespy.components import CycleCloser, Pump, Condenser, Turbine, SimpleHeatExchanger, Source, Sink
from tespy.connections import Connection
from tespy.networks import Network

# Create network with units
nw = Network(fluids=['water'], T_unit='C', p_unit='bar', h_unit='kJ / kg')

# Define components
cc = CycleCloser('cycle closer')
sg = SimpleHeatExchanger('steam generator')
mc = Condenser('main condenser')
tu = Turbine('steam turbine')
fp = Pump('feed pump')
cwso = Source('cooling water source')
cwsi = Sink('cooling water sink')

# Define connections (main cycle)
c1 = Connection(cc, 'out1', tu, 'in1', label='1')   # Boiler outlet (to turbine)
c2 = Connection(tu, 'out1', mc, 'in1', label='2')   # Turbine outlet (to condenser)
c3 = Connection(mc, 'out1', fp, 'in1', label='3')   # Condenser outlet (to pump)
c4 = Connection(fp, 'out1', sg, 'in1', label='4')   # Pump outlet (to boiler inlet)
c0 = Connection(sg, 'out1', cc, 'in1', label='0')   # Boiler outlet to cycle closer

# Cooling water connections
c11 = Connection(cwso, 'out1', mc, 'in2', label='11')  # Cooling water inlet
c12 = Connection(mc, 'out2', cwsi, 'in1', label='12')  # Cooling water outlet

# Add connections to network
nw.add_conns(c1, c2, c3, c4, c0, c11, c12)

# Set component parameters
mc.set_attr(pr1=1, pr2=0.98)    # Condenser pressure losses
sg.set_attr(pr=0.9)             # Boiler pressure loss
tu.set_attr(eta_s=0.9)          # Turbine isentropic efficiency
fp.set_attr(eta_s=0.75)         # Pump isentropic efficiency

# Set boundary conditions (minimal and correct)
# Set main steam conditions at boiler outlet (turbine inlet)
c1.set_attr(T=600, p=150, m=532, fluid={'water': 1})  # Boiler outlet/superheated steam
c2.set_attr(p=0.1)                                    # Condenser pressure
# Do NOT set pressure at c4 (pump outlet/boiler inlet)
c11.set_attr(T=20, p=1.2, fluid={'water': 1})         # Cooling water in
c12.set_attr(T=30)                                    # Cooling water out

# Note: Do NOT set temperature or enthalpy at c4 (boiler inlet), TESPy calculates it

# Solve the network
nw.solve('design')

# Print results
nw.print_results()

# Display boiler inlet (pump outlet) and boiler outlet (to turbine) parameters
print(f"Boiler Inlet (pump outlet) - Connection c4:")
print(f"  Temperature: {c4.T.val:.2f} °C")
print(f"  Pressure: {c4.p.val:.2f} bar")
print(f"  Enthalpy: {c4.h.val:.2f} kJ/kg\n")

print(f"Boiler Outlet (to turbine) - Connection c1:")
print(f"  Temperature: {c1.T.val:.2f} °C")
print(f"  Pressure: {c1.p.val:.2f} bar")
print(f"  Enthalpy: {c1.h.val:.2f} kJ/kg")

# Save network for later use (e.g., in Streamlit dashboard)
nw.save('rankine_model')






