import streamlit as st
from datetime import datetime, timedelta
from dateutil import parser
from ressources.setup import *

framework()

col1, col2 = st.sidebar.columns(2)
initgas = col1.multiselect(f"Initial gas in:", ['Ar', 'H2'], ["Ar"])
wait = col2.number_input("Waiting before start [s]:", 0, 2000, 30)

col1, col2, col3 = st.sidebar.columns(3)
Nsteps = col1.number_input("Number of steps in recipe:", 1, 2000, 4)
N = col2.number_input("N Cycles:", 
        min_value=0, step=1, value=default["N"], key="N")
recipe = col3.text_input("Recipe name:", "ALD")
times = []
valves = []
plasma = []
for step in range(Nsteps):
    col1, col2, col3 = st.sidebar.columns(3)
    valves.append(col1.multiselect(f"**Step {step+1} - Gas:**", ['TEB', 'Ar', 'H2'], default["valves"][step], key=f"valve{1+step}"))
    times.append(col2.number_input(f"**Step {step+1} - Time [s]:**", min_value=0., step=1., value=default["times"][step], format="%.3f", key=f"t{1+step}"))
    plasma.append(col3.number_input(f"**Step {step+1} - Plasma [W]:**", min_value=0, step=10, value=default["plasma"][step], key=f"plasma{1+step}"))

print_tot_time(sum(times)*N)

# # # # # # # # # # # # # # # # # # # # # # # #
# STOP button
# # # # # # # # # # # # # # # # # # # # # # # #

layout = st.sidebar.columns(2)

STOP = layout[0].button("STOP PROCESS")
if STOP:
    end_time = datetime.now().strftime(f"%Y-%m-%d-%H:%M:%S")
    if len(st.session_state['logname']) > 0:
        duration = f"{parser.parse(end_time)-parser.parse(st.session_state['start_time'])}"
        write_to_log(st.session_state['logname'], end=end_time, 
                    duration=duration,
                    ending = "forced")
    end_recipe()

# # # # # # # # # # # # # # # # # # # # # # # #
# GO button
# # # # # # # # # # # # # # # # # # # # # # # #
GObutton = layout[1].button('GO')
if GObutton:
    Recipe(times=times, valves=valves, plasma=plasma, N=N, initgas=initgas, wait=wait)

# # # # # # # # # # # # # # # # # # # # # # # #
# Show recipe graph
# # # # # # # # # # # # # # # # # # # # # # # #

allsteps=[initgas]+valves
for i in range(len(allsteps)):
    if len(allsteps[i])==0:
        if i==0:
            st.warning("**!! Initialization with no gas input, check it's not an error. !!**")
        else:
            st.warning(f"**!! Step {i} with no gas input, check it's not an error. !!**")

showgraph(initgas=initgas, wait=wait, plasma=plasma, valves=valves, times=times, Nsteps=Nsteps)
