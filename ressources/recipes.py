# # # # # # # # # # # # # # # # # # # # # # # #
# Define default recipes
# # # # # # # # # # # # # # # # # # # # # # # #

recPEALD = {
    "recipe" : "PEALD",
    "initgas": ["Ar"],
    "wait"   : 10,
    "fingas" : ["Ar"],
    "waitf"  : 10,
    "N"      : 100,
    "Nsteps" : 4,
    "valves" : [["TEB", "Ar"], ["Ar"], ["H2"], ["Ar"]],
    "times"  : [1., 40., 10., 40.],
    "plasma" : [0,0,30,0],
    }

recALD = {
    "recipe" : "ALD",
    "initgas": ["Ar"],
    "wait"   : 10,
    "fingas" : ["Ar"],
    "waitf"  : 10,
    "N"      : 100,
    "Nsteps" : 4,
    "valves" : [["TEB", "Ar"], ["Ar"], ["H2"], ["Ar"]],
    "times"  : [1., 40., 10., 40.],
    "plasma" : [0, 0, 0, 0]
    }

recCVD = {
    "recipe" : "CVD",
    "initgas": ["H2"],
    "wait"   : 240,
    "fingas" : ["H2"],
    "waitf"  : 1800,
    "N"      : 1,
    "Nsteps" : 2,
    "valves" : [["TEB", "Ar"], ["H2"]],
    "times"  : [10., 10.],
    "plasma" : [0, 0]
    }

recPECVD = {
    "recipe" : "PECVD",
    "initgas": ["H2"],
    "wait"   : 240,
    "fingas" : ["H2"],
    "waitf"  : 1800,
    "N"      : 1,
    "Nsteps" : 2,
    "valves" : [["TEB", "Ar"], ["H2"]],
    "times"  : [10., 10.],
    "plasma" : [0, 30]
    }

recPulsedCVD = {
    "recipe" : "Pulsed CVD",
    "initgas": ["H2"],
    "wait"   : 240,
    "fingas" : ["H2"],
    "waitf"  : 1800,
    "N"      : 100,
    "Nsteps" : 2,
    "valves" : [["TEB", "Ar"], ["H2"]],
    "times"  : [.25, 40.],
    "plasma" : [0, 0]
    }

recPulsedPECVD = {
    "recipe" : "Pulsed PECVD",
    "initgas": ["H2"],
    "wait"   : 240,
    "fingas" : ["H2"],
    "waitf"  : 1800,
    "N"      : 100,
    "Nsteps" : 3,
    "valves" : [["TEB", "Ar"], ["H2"], ["H2"]],
    "times"  : [.250, 10., 40.],
    "plasma" : [0, 30, 0]
    }

recPurge = {
    "recipe" : "Purge",
    "initgas": ["Ar"],
    "wait"   : 0,
    "fingas" : ["Ar"],
    "waitf"  : 1,
    "N"      : 1,
    "Nsteps" : 1,
    "valves" : [["TEB", "Ar"]],
    "times"  : [180.],
    "plasma" : [0]
    }