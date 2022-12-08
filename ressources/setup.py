import streamlit as st
import graphviz
import time
from datetime import datetime, timedelta
from dateutil import parser
import smbus
import ressources.citobase as cb
from tempfile import mkstemp
from shutil import move, copymode
import os

st.set_page_config(
    page_title="ALD – CVD Process",
    page_icon=":hammer_and_pick:",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://lmi.cnrs.fr/author/colin-bousige/',
        'Report a bug': "https://lmi.cnrs.fr/author/colin-bousige/",
        'About': """
        ## ALD – CVD Process
        Version date 2021-10-27.

        This app was made by [Colin Bousige](https://lmi.cnrs.fr/author/colin-bousige/). Contact me for support, requests, or to signal a bug.
        """
    }
)

# # # # # # # # # # # # # # # # # # # # # # # #
# Define default variables and relays
# # # # # # # # # # # # # # # # # # # # # # # #

# Relays from the hat are commanded with I2C
DEVICE_BUS = 1
bus = smbus.SMBus(DEVICE_BUS)

# Relays attribution
# Hat adress, relay number
relays = {
    "TEB": (0x10, 1),
    "H2": (0x10, 2),
    "Ar": (0x10, 3)
}

# IP Address of the Cito Plus RF generator, connected by Ethernet
# cito_address = "169.254.1.1"
# citoctrl = cb.CitoBase(host_mode = 0, host_addr = cito_address) # 0 for Ethernet

# Address of the Cito Plus RF generator, connected by RS232->USB
cito_address = "/dev/ttyUSB0"
citoctrl = cb.CitoBase(host_mode = 1, host_addr = cito_address)

# For writing into the log at the end of the recipe, 
# whether it's a normal or forced ending
if 'logname' not in st.session_state:
    st.session_state['logname'] = ''
if 'start_time' not in st.session_state:
    st.session_state['start_time'] = ''
if 'cycle_time' not in st.session_state:
    st.session_state['cycle_time'] = ''

# # # # # # # # # # # # # # # # # # # # # # 
# Functions handling gas lines
# # # # # # # # # # # # # # # # # # # # # # 

def turn_ON(gas):
    """
    Open relay from the hat with I2C command
    """
    DEVICE_ADDR, rel = relays[gas]
    # print(f"ON - {gas}")
    if gas != "Ar":
        bus.write_byte_data(DEVICE_ADDR, rel, 0xFF)
    else:
        bus.write_byte_data(DEVICE_ADDR, rel, 0x00) # "Ar" Normally Open


def turn_OFF(gas):
    """
    Close relay from the hat with I2C command
    """
    DEVICE_ADDR, rel = relays[gas]
    # print(f"OFF - {gas}")
    if gas != "Ar":
        bus.write_byte_data(DEVICE_ADDR, rel, 0x00)
    else:
        bus.write_byte_data(DEVICE_ADDR, rel, 0xFF) # "Ar" Normally Open


# # # # # # # # # # # # # # # # # # # # # # 
# Functions handling Plasma
# # # # # # # # # # # # # # # # # # # # # # 

def set_plasma(plasma, logname=None):
    """
    Open the connection to the RF generator and setup the plasma power
    """
    if citoctrl.open():
        citoctrl.set_power_setpoint_watts(plasma)  # set the rf power
        st.success("Connection with RF generator OK.")
        st.info(f"Setpoint: {plasma} W - Value: {citoctrl.get_power_setpoint_watts()[1]} W")
        if logname is not None:
            write_to_log(logname, plasma_active="Yes")
    else:
        st.error("Can't open connection to the RF generator.")
        if logname is not None:
            write_to_log(logname, plasma_active="No")
        return(False)


def HV_ON():
    """
    Turn HV on
    """
    # print(f"Plasma ON")
    if citoctrl.open():
        citoctrl.set_rf_on()


def HV_OFF():
    """
    Turn HV off
    """
    # print(f"Plasma OFF")
    if citoctrl.open():
        citoctrl.set_rf_off()

# # # # # # # # # # # # # # # # # # # # # # 
# Functions handling log file writing/updating
# # # # # # # # # # # # # # # # # # # # # # 

def append_to_file(logfile="log.txt", text=""):
    """
    Function to easily append text to a logfile
    """
    with open(logfile, 'a') as fd:
        fd.write(f'{text}\n')


def replacement(filepath, pattern, replacement):
    """
    Function to replace a pattern in a file
    """
    # Creating a temp file
    fd, abspath = mkstemp()
    with os.fdopen(fd, 'w') as file1:
        with open(filepath, 'r') as file0:
            for line in file0:
                file1.write(line.replace(pattern, replacement))
    copymode(filepath, abspath)
    os.remove(filepath)
    move(abspath, filepath)


def update_cycle(logname, i, N):
    """
    Function to write the current cycle number in the logfile
    """
    if i == 0:
        write_to_log(logname, cycles_done=f"{i+1}/{N}")
    else:
        replacement(logname,
                    f"cycles_done      {i}/{N}",
                    f"cycles_done      {i+1}/{N}")


def write_to_log(logname, **kwargs):
    """
    Function to easily create and update a logfile
    """
    os.makedirs(os.path.dirname(logname), exist_ok=True)
    toprint = {str(key): str(value) for key, value in kwargs.items()}
    append_to_file(logname, text='\n'.join('{:15}  {}'.format(
        key, value) for key, value in toprint.items()))

# # # # # # # # # # # # # # # # # # # # # # 
# Functions handling UI
# # # # # # # # # # # # # # # # # # # # # # 

def framework():
    """
    Defines the style and the positions of the printing areas
    """
    global c1, c2, remcycletext, remcycle, remcyclebar, step_print
    global remtottimetext, remtottime, remtime, final_time_text, final_time
    c1, c2 = st.columns((2, 1))
    remcycletext = c1.empty()
    remcycle = c1.empty()
    remcyclebar = c1.empty()
    step_print = c1.empty()
    remtottimetext = c2.empty()
    remtottime = c2.empty()
    remtime = c2.empty()
    final_time_text = c2.empty()
    final_time = c2.empty()
    with open("ressources/style.css") as f:
        st.markdown('<style>{}</style>'.format(f.read()),
                    unsafe_allow_html=True)


def print_tot_time(tot):
    """
    Print total estimated time and estimated ending time
    """
    finaltime = datetime.now() + timedelta(seconds=tot)
    remcycletext.write("# Total Time:\n")
    tot = int(tot)
    totmins, totsecs = divmod(tot, 60)
    tothours, totmins = divmod(totmins, 60)
    tottimer = '{:02d}:{:02d}:{:02d}'.format(tothours, totmins, totsecs)
    remcycle.markdown(
        "<div><h2><span class='highlight green'>"+tottimer+"</h2></span></div>",
        unsafe_allow_html=True)
    final_time_text.write("# Ending Time:\n")
    final_time.markdown(
        "<div><h2><span class='highlight red'>"+finaltime.strftime("%H:%M") +
        "</h2></span></div>", unsafe_allow_html=True)


def countdown(t, tot):
    """
    Print time countdown and total remaining time
    """
    remtottimetext.write("# Remaining Time:\n")
    tot = int(tot)
    while t>0:
        if t >= 1:
            mins, rest = divmod(t, 60)
            secs, mil = divmod(rest, 1)
            timer = '{:02d}:{:02d}:{:03d}'.format(int(mins), int(secs), int(mil*1000))
            remtime.markdown(
                f"<div><h2>Current step: <span class='highlight blue'>{timer}</h2></span></div>",
                unsafe_allow_html=True)
            totmins, totsecs = divmod(tot, 60)
            tothours, totmins = divmod(totmins, 60)
            tottimer = '{:02d}:{:02d}:{:02d}'.format(
                tothours, totmins, totsecs)
            remtottime.markdown(
                f"<div><h2>Total: <span class='highlight blue'>{tottimer}</h2></span></div>",
                unsafe_allow_html=True)
            time.sleep(1)
            t -= 1
            tot -= 1
        else:
            time.sleep(t)
            t -= 1


def showgraph(initgas=["Ar"], wait=30, plasma=[10.], valves=["Ar"], times=[10.],
              Nsteps=4, highlight=-1, N=100):
    """
    Display a GraphViz chart of the recipe
    """
    graph = graphviz.Digraph()
    graph.attr(layout="circo", rankdir='LR')
    graph.attr('node', shape="box", style="rounded")
    graph.attr(label=f'                                          Repeat {N} times')
    if highlight==-2:
        graph.node("A",f"{' + '.join(initgas)}\n{wait} s", 
                   style='rounded,filled', fillcolor="lightseagreen")
    else:
        graph.node("A",f"{' + '.join(initgas)}\n{wait} s")
    for i in range(Nsteps):
        pl=f"\nPlasma {plasma[i]} W" if plasma[i]>0 else ""
        init = f'{i+1}. {" + ".join(valves[i])}\n{times[i]} s{pl}'
        if plasma[i]>0 and highlight==-1:
            graph.node(str(i), init, style='rounded,filled', fillcolor="cyan")
        elif highlight>=0 and i==highlight and plasma[i]==0:
            graph.node(str(i), init, style='rounded,filled', fillcolor="lightseagreen")
        elif highlight>=0 and i==highlight and plasma[i]>0:
            graph.node(str(i), init, style='rounded,filled', fillcolor="cyan")
        else:
            graph.node(str(i), init)
    graph.edges(["A0"]+[f"{i}{(i+1)%(Nsteps)}" for i in range(Nsteps)])
    step_print.graphviz_chart(graph)


# # # # # # # # # # # # # # # # # # # # # # 
# Functions handling initialization and ending of recipe
# # # # # # # # # # # # # # # # # # # # # # 

def initialize(initgas=["Ar"], wait=-1, valves=["Ar"], times=[10.], 
               plasma=[0], tot=10, N=100):
    """
    Make sure the relays are closed
    """
    if len(initgas) == 0:
        turn_OFF("TEB")
        turn_OFF("Ar")
        turn_OFF("H2")
    else:
        for gas in ['Ar','TEB','H2']:
            if gas not in initgas:
                turn_OFF(gas)
            else:
                turn_ON(gas)
    if wait>0:
        showgraph(initgas=initgas, wait=wait, plasma=plasma, valves=valves, 
                  times=times, Nsteps=len(times), highlight=-2, N=N)
        remcycletext.write("# Cycle number:\n")
        remcycle.markdown(f"<div><h2><span class='highlight green'>0 / {N}</h2></span></div>",
                          unsafe_allow_html=True)
        remcyclebar.progress(int((0)/N*100))
        countdown(wait, tot)


def end_recipe():
    """
    Ending procedure for recipes
    """
    turn_OFF("TEB")
    turn_OFF("H2")
    turn_ON("Ar")
    if citoctrl.open():
        HV_OFF()
        citoctrl.close()
    st.experimental_rerun()


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#  RECIPE DEFINITIONS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

def Recipe(valves=["Ar"], times=[10.], plasma=[0], N=100, recipe="ALD", 
           initgas=["Ar"], wait=30, fingas=["Ar"], waitf=30):
    """
    Definition of recipe
    """
    tot = sum(times)*N+wait+waitf
    start_time = datetime.now().strftime(f"%Y-%m-%d-%H:%M:%S")
    st.session_state['start_time'] = start_time
    st.session_state['logname'] = f"Logs/{start_time}_{recipe}.txt"
    st.session_state['cycle_time'] = (tot-waitf-wait)/N
    stepslog = ["    - %-11s%.3lf s - Plasma %d W" % (' + '.join(v), t, p) for v,t,p in zip(valves,times,plasma)]
    stepslog = [f"  - Init.:       {' + '.join(initgas)}, {wait} s"] + stepslog
    stepslog = stepslog + [f"  - Final.:      {' + '.join(fingas)}, {waitf} s"]
    stepslog = "\n"+"\n".join(stepslog)
    write_to_log(st.session_state['logname'], recipe=recipe, start=start_time,
                 steps=stepslog, N=N, time_per_cycle=timedelta(seconds=st.session_state['cycle_time']))
    initialize(initgas=initgas, wait=wait, valves=valves, times=times, 
               plasma=plasma, tot=tot, N=N)
    tot = tot - wait
    for i in range(N):
        for step in range(len(times)):
            remcycletext.write("# Cycle number:\n")
            remcycle.markdown(f"<div><h2><span class='highlight green'>{i+1} / {N}</h2></span></div>",
                                unsafe_allow_html=True)
            remcyclebar.progress(int((i+1)/N*100))
            # Steps
            for v in valves[step]:
                turn_ON(v)
            if plasma[step]>0:
                set_plasma(plasma[step])
                HV_ON()
            showgraph(initgas=initgas, wait=wait, plasma=plasma, valves=valves, N=N,
                      times=times, Nsteps=len(times), highlight=step)
            countdown(times[step], tot)
            tot = tot-times[step]
            for v in valves[step]:
                if v not in valves[(step+1)%len(times)]:
                    turn_OFF(v)
            if plasma[step]>0:
                HV_OFF()
        update_cycle(st.session_state['logname'], i, N)
    showgraph(initgas=initgas, wait=wait, plasma=plasma, valves=valves, N=N,
              times=times, Nsteps=len(times), highlight=-1)
    for v in fingas:
        turn_ON(v)
    remcycletext.write("# Finalization....\n")
    countdown(waitf, tot)
    end_time = datetime.now().strftime(f"%Y-%m-%d-%H:%M:%S")
    st.balloons()
    time.sleep(2)
    write_to_log(st.session_state['logname'], end=end_time,
                    duration=f"{parser.parse(end_time)-parser.parse(start_time)}",
                    ending="normal")
    end_recipe()


