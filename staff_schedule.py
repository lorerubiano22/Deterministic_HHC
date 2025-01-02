from gurobipy import *
import openpyxl as oxl
from openpyxl.styles import Alignment
import numpy as np
import pandas as pd

model = Model('optimizer')

def solve(I1,                   # set of all clients with staff 1 requirement drop off node
          I2,                   # set of all clients with staff 2 requirement
          I3,                   # set of all clients with staff 3 requirement
          EST_client, 
          LST_client, 
          STD_client,
          staff,                # set of all staff
          S1,                   # set of all staff level 1
          S2,                   # set of all staff level 2
          S3,                   # set of all staff level 3
          ):

    node_staff_1 = [] # combinations of i and s with qualification 1 list of Tuples with i as the node and s as the allowed staff
    node_staff_2 = [] # combinations of i and s with qualification 2
    node_staff_3 = [] # combinations of i and s with qualification 3
    
    for i in I1:
        for s in S1:
            node_staff_1 += [(i,s)]
    for i in I2:
        for s in S2:
            node_staff_2 += [(i,s)]
    for i in I3:
        for s in S3:
            node_staff_3 += [(i,s)]
    
    client_staff_tuple = node_staff_1 + node_staff_2 + node_staff_3

    clients = I1 + I2 + I3
   

    M = 1000

    """Variable Declaration"""

    W = {}
    Dt = {}
    Pt = {}
    predecessor = {}
    use_staff = {}
    working_hours = {}

    
    for (c,s) in client_staff_tuple:
        # is staff s performing task at client i of appropriate level (=1) or not (=0):
        W[c,s] = model.addVar(name=f'W_{c}_{s}', vtype='b') 
        # at what time is staff s dropped at node i:
        Dt[c,s] = model.addVar(name=f'Dt_{c}_{s}', vtype='c', lb=0) 
        # at what time is staff s picked up from node ip:
        Pt[c,s] = model.addVar(name=f'Pt_{c}_{s}', vtype='c', lb=0)  
    # is c predecessing k:
    for c in clients:
        for k in clients:
            if c != k:
                for s in staff:
                    if ((c,s) in client_staff_tuple) and ((k,s) in client_staff_tuple):
                        predecessor[c,k,s] = model.addVar(name=f'predecessor_{c}_{k}_{s}', vtype='b')
    for (c,s) in client_staff_tuple:
        if (c,s) in client_staff_tuple:
            predecessor['MC',c,s] = model.addVar(name=f'predecessor_MC_{c}_{s}', vtype='b')
    for s in staff:
        use_staff[s] = model.addVar(name=f'use_staff_{s}', vtype='b')
        working_hours[s] = model.addVar(name=f'working_hours_{s}')
    
    """Constraints"""

    for c in clients:
        model.addConstr(quicksum(W[c,s] for s in staff if (c,s) in client_staff_tuple) == 1)
    for s in staff:
        # ensure that the latest allowed starting time is always respected:
        model.addConstrs((1 - W[c,s]) * M + int(LST_client.get(c)) >= Dt[c,s] for (c,s) in client_staff_tuple)
        # ensure that the earliest allowed starting time is always respected:
        model.addConstrs((W[c,s] - 1) * M + int(EST_client.get(c)) <= Dt[c,s] for (c,s) in client_staff_tuple)
        # difference between drop off time at client node i and pick up time at client partner node ip has to be
        # larger or equal to the standard service time:
        model.addConstrs((1 - W[c,s]) * M + Pt[c,s] -  Dt[c,s] >= int(STD_client.get(c)) for (c,s) in client_staff_tuple)
    
    for c in clients:
        for k in clients:
            if c != k:
                for s in staff:
                    if ((c,s) in client_staff_tuple) and ((k,s) in client_staff_tuple):
                        # if c and k are serviced by same staff and c is direct predecessor of k, make sure that there are 10 minutes between:
                        model.addConstr((1 - predecessor[c,k,s]) * M + Dt[k,s] >= Pt[c,s] + 10)
                        
    for s in staff:
        model.addConstr(quicksum(predecessor['MC',c,s] for c in clients if (c,s) in client_staff_tuple) == use_staff[s])
    for c in clients:
        model.addConstr(quicksum(predecessor['MC',c,s] for s in staff if (c,s) in client_staff_tuple) <= 1)
    for s in staff:
        for k in clients:
            if (k,s) in client_staff_tuple:
                model.addConstr(quicksum(predecessor[c,k,s] for c in clients if (c,s) in client_staff_tuple if c != k) + predecessor['MC',k,s] == W[k,s])
                model.addConstr(quicksum(predecessor[k,c,s] for c in clients if (c,s) in client_staff_tuple if c != k) <= W[k,s])
    for s in staff:
        for c in clients:
            if (c,s) in client_staff_tuple:
                model.addConstr(use_staff[s] >= W[c,s])
                model.addConstr(working_hours[s] <= 460)
    
    for s in staff:
        for c in clients:
            for k in clients:
                if k!=c:
                    if ((c,s) in client_staff_tuple) & ((k,s) in client_staff_tuple):
                        model.addConstr(working_hours[s] >= Pt[k,s] - Dt[c,s]) #pickup minus drop off!

    for i in range(len(S1)-1):
        model.addConstr(use_staff[S1[i]] >= use_staff[S1[i+1]])
    for i in range(len(S2)-1):
        model.addConstr(use_staff[S2[i]] >= use_staff[S2[i+1]])
    for i in range(len(S3)-1):
        model.addConstr(use_staff[S3[i]] >= use_staff[S3[i+1]])


    """Optimization and Schedule"""

    model.setObjective(quicksum(use_staff[s] for s in staff))
    model.setParam(GRB.Param.MIPFocus, 2)
    model.optimize()
    if model.SolCount > 0:
        client_staff_match = {}
        for s in staff:
            schedule = []
            if round(use_staff[s].getAttr('X')) == 1:
                for c in clients:
                    if (c,s) in client_staff_tuple:
                        if round(predecessor['MC',c,s].getAttr('X')) == 1:
                            current_client = c
                            schedule += [c]
                found_succesor = True
                while found_succesor:
                    found_succesor = False
                    for c in clients:
                        if ((c,s) in client_staff_tuple) and (c != current_client):
                            if round(predecessor[current_client,c,s].getAttr('X')) == 1:
                                found_succesor = True
                                current_client = c
                                schedule += [c]
                client_staff_match[s] = schedule
            print(f'The schedule for staff {s} is :')
            for c in schedule:
                print(c)
        print(client_staff_match)
        

        variable_groups = {}
        for var in model.getVars():
            name = var.varName.split('_')[0]  # Extract variable name without index
            if name not in variable_groups:
                variable_groups[name] = []
            variable_groups[name].append(var)

        # Save output to a file
        output_file_path = "outputs/decision_variables.txt"
        nonzero_output_file_path = "outputs/nonzero_decision_variables.txt"
        with open(output_file_path, "w") as output_file:

            # Print decision variables grouped by their names to the file
            for name, vars in variable_groups.items():
                output_file.write(f"Variables with name '{name}':\n")
                for var in vars:
                    output_file.write(f"{var.varName} = {var.x}\n")

        with open(nonzero_output_file_path, "w") as output_file:

            # Print decision variables grouped by their names to the file
            for name, vars in variable_groups.items():
                output_file.write(f"Variables with name '{name}':\n")
                for var in vars:
                    if var.x >= 0.99:
                        output_file.write(f"{var.varName} = {np.round(var.x,0)}\n")
        return client_staff_match
    elif model.Status == GRB.INFEASIBLE:
        print("Model is infeasible.")
        model.computeIIS()
        model.write("outputs/infeasibility_report.ilp")
        return None






