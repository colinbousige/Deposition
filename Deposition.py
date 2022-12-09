import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser
from ressources.setup import *

framework()

if 'default' not in st.session_state:
    st.session_state['default'] = recPEALD

st.write("---")
main = st.columns(5)

if main[0].button("ALD"):
    st.session_state['default'] = recALD

if main[0].button("PEALD"):
    st.session_state['default'] = recPEALD

if main[1].button("CVD"):
    st.session_state['default'] = recCVD

if main[1].button("PECVD"):
    st.session_state['default'] = recPECVD

if main[2].button("Pulsed CVD"):
    st.session_state['default'] = recPulsedCVD

if main[2].button("Pulsed PECVD"):
    st.session_state['default'] = recPulsedPECVD

if main[3].button("Purge"):
    st.session_state['default'] = recPurge

uploaded_file = main[4].file_uploader("**Import recipe:**", label_visibility="collapsed")
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, sep="|")
    st.session_state['default'] = {
        "recipe" : df["recipe"][0],
        "initgas": df["initgas"][0].split(","),
        "wait"   : int(df["wait"][0]),
        "fingas" : df["fingas"][0].split(","),
        "waitf"  : int(df["waitf"][0]),
        "N"      : int(df["N"][0]),
        "Nsteps" : int(df["Nsteps"][0]),
        "valves" : [v.split(";") for v in df["valves"][0].split(",")],
        "times"  : [float(t) for t in df["times"][0].split(",")],
        "plasma" : [int(p) for p in df["plasma"][0].split(",")]
        }

default = st.session_state['default']

st.sidebar.write("### Initialization______________________________")
col1, col2 = st.sidebar.columns(2)
initgas = col1.multiselect(f"Initial gas in:", ['Ar', 'H2'], default["initgas"])
wait = col2.number_input("Waiting before start [s]:", 0, 2000, default["wait"])

st.sidebar.write("### Recipe___________________________________")
col1, col2, col3 = st.sidebar.columns(3)
Nsteps = col1.empty()
Nsteps = col1.number_input("Number of steps in recipe:", min_value=1, max_value=20, value=default["Nsteps"])
N = col2.number_input("N Cycles:", min_value=0, step=1, value=default["N"], key="N")
recipe = col3.text_input("Recipe name:", default["recipe"])
times = []
valves = []
plasma = []

for step in range(Nsteps):
    col1, col2, col3 = st.sidebar.columns(3)
    dv = default["valves"][step] if step < len(default["valves"]) else ["Ar"]
    dt = default["times"][step] if step < len(default["times"]) else 10.
    dp = default["plasma"][step] if step < len(default["plasma"]) else 0
    valves.append(col1.multiselect(f"**Step {step+1} - Gas:**", ['TEB', 'Ar', 'H2'], 
                  default=dv, key=f"valve{1+step}"))
    times.append(col2.number_input(f"**Step {step+1} - Time [s]:**", max_value=1.e5,
                 min_value=0., step=1., value=dt, format="%.3f", key=f"t{1+step}"))
    plasma.append(col3.number_input(f"**Step {step+1} - Plasma [W]:**", max_value=600,
                 min_value=0, step=10, value=dp, key=f"plasma{1+step}"))

st.sidebar.write("### Finalization______________________________")
col1, col2 = st.sidebar.columns(2)
fingas = col1.multiselect(f"Final gas in:", ['Ar', 'H2'], default["fingas"])
waitf = col2.number_input("Final waiting [s]:", min_value=0, value=default["waitf"])

print_tot_time(sum(times)*N+wait+waitf)

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
    Recipe(times=times, valves=valves, plasma=plasma, N=N, 
           initgas=initgas, wait=wait, fingas=fingas, waitf=waitf)

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

showgraph(initgas=initgas, wait=wait, plasma=plasma, valves=valves, 
          times=times, Nsteps=Nsteps, N=N)


csv = f"""recipe|initgas|wait|fingas|waitf|N|Nsteps|valves|times|plasma
{recipe}|{",".join(initgas)}|{wait}|{",".join(fingas)}|{waitf}|{N}|{Nsteps}|{",".join(";".join(v) for v in valves)}|{",".join(str(t) for t in times)}|{",".join(str(p) for p in plasma)}"""

main[3].download_button("**Save recipe**",
    data=csv,
    file_name=f"{datetime.now().strftime(f'%Y-%m-%d-%H:%M:%S')}_{recipe}.csv",
    mime='text/csv',
)