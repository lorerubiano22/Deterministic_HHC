from gurobipy import *
import openpyxl as oxl
from openpyxl.styles import Alignment
import numpy as np
import pandas as pd

model = Model('optimizer')

def solve(I_total,              # set of all customers and Medical center
          I0,                   # set of all patients pick up
          I_0,                  # set of all patients drop off
          I1,                   # set of all clients with staff 1 requirement drop off node
          I_1,                  # set of all clients with staff 1 requirement pick up node
          I2,                   # set of all clients with staff 2 requirement
          I_2,                  # set of all clients with staff 2 requirement pick up node
          I3,                   # set of all clients with staff 3 requirement
          I_3,                  # set of all clients with staff 3 requirement pick up node
          tt,                   # set of travel times (call the travel time from i to j by punching in "tt[j].get(i)"
          EST_patient, 
          LST_patient, 
          STD_patient, 
          EST_client, 
          LST_client, 
          STD_client,           
          S1,                   # set of all staff level 1
          S2,                   # set of all staff level 2
          S3,                   # set of all staff level 3
          vehicle_capacity,     # vehicle_capacity
          number_of_vehicles,   # how many vehicles are available
          allowed_routes,       # how many different routes are allowed
          allow_wait_staff,     # is staff allowed to wait at clients
          allow_delay_clients,  # is delay at clients allowed
          allow_wait_patients,  # are patients allowed to wait
          allow_overtime,       # is staff allowed to work overtime
          max_wait_staff,       # how long is staff allowed to wait at most
          max_wait_patiens,     # how long are patiens allowed to wait at most
          client_staff_match,   # prepared schedule for staff
          level_1,              # shift cost for staff level 1
          level_2,              # shift cost for staff level 2
          level_3,              # shift cost for staff level 3
          over_time,            # additional wage surplus for overtime
          driver,               # shift cost for driver
          car_fixed,            # fixed cost for a car being used
          fuel_cost             # fuel cost per minute
          ):
    print('Start')
    staff = client_staff_match.keys()
    staff1 =[]
    staff2 = []
    staff3 = []
    for s in staff:
        if s in S1:
            staff1 += [s]
        elif s in S2:
            staff2 += [s]
        elif s in S3:
            staff3 += [s]

    node_staff_tuple = []
    for s in staff:
        node_staff_tuple += [('MCd',s)]
        for i in client_staff_match[s]:
            node_staff_tuple += [(i,s)]

    I_dict = {}
    I0_dict = {}
    for i in range(len(I0)):
        I0_dict[I0[i]] = I_0[i]
        I_dict[I0[i]] = I_0[i]
    
    I1_dict = {}
    for i in range(len(I1)):
        I1_dict[I1[i]] = I_1[i]
        I_dict[I1[i]] = I_1[i]
    
    I2_dict = {}
    for i in range(len(I2)):
        I2_dict[I2[i]] = I_2[i]
        I_dict[I2[i]] = I_2[i]
    
    I3_dict = {}
    for i in range(len(I3)):
        I3_dict[I3[i]] = I_3[i]
        I_dict[I3[i]] = I_3[i]
    
    I_dict['MCd'] = 'MC'
    

    M = 1000

    """Variable Declaration"""

    X = {}
    t = {}
    D = {}
    P = {}
    Dt = {}
    Pt = {}
    p = {}
    d = {}
    pt = {}
    dt = {}
    y = {}
    wait_at_client_before = {}
    wait_at_client_after = {}
    delay_at_client = {}
    wait_at_MC_before = {}
    wait_at_MC_after = {}
    use_car = {}
    route_car_match = {}
    predecessor = {}
    start_car_travel = {}
    end_car_travel = {}
    car_travel = {}
    overtime = {}
    capacity_used = {}
    route_len = {}
    
    for i in I_total:
        for j in I_total:
            if i != j:
                for r in range(allowed_routes):
                    # does route r visit node j after node i (=1) or not (=0):
                    X[i,j,r] = model.addVar(name=f'X_{i}_{j}_{r}', vtype='b') 

    for i in I_total: 
        for r in range(allowed_routes):
            # at which time in the route is the route r arriving at node i:
            t[i,r] = model.addVar(name=f't_{i}_{r}', vtype='c', lb=0) 

    # t = model.addVars(I_total, range(allowed_routes), name='t', vtype='b')
    
    for (i,s) in node_staff_tuple:
        # at what time is staff s dropped at node i:
        Dt[i,s] = model.addVar(name=f'Dt_{i}_{s}', vtype='c', lb=0) 
        # at what time is staff s picked up from node ip:
        Pt[I_dict.get(i),s] = model.addVar(name=f'Pt_{I_dict.get(i)}_{s}', vtype='c', lb=0) 
        if allow_wait_staff:
            # how long has staff s to wait at client i before beginning service:
            wait_at_client_before[i,s] = model.addVar(name=f'wait_at_client_before_{s}_{i}', vtype='c', lb=0)
            wait_at_client_after[i,s] = model.addVar(name=f'wait_at_client_after_{s}_{i}', vtype='c', lb=0)
        for r in range(allowed_routes): 
            # does route r drop staff s off at node i (=1) or not (=0):
            D[i,s,r] = model.addVar(name=f'D_{i}_{s}_{r}', vtype='b')
            # does route r pick staff s up from node ip (=1) or not (=0):
            P[I_dict.get(i),s,r] = model.addVar(name=f'P_{I_dict.get(i)}_{s}_{r}', vtype='b') 

    for r in range(allowed_routes):
        for i in I_total:
            # is route r going to node i (=1) or not (=0):
            y[i,r] = model.addVar(name=f'y_{i}_{r}', vtype='b') 
        for r2 in range(allowed_routes):
            if r != r2:
                # does route r start before route r2 (=1) or not (=0):
                predecessor[r,r2] = model.addVar(name=f'predecessor_{r}_{r2}', vtype='b')             
    
    for i in I0:
        # at what time is patient i dropped off at MC:
        dt[i] = model.addVar(name=f'dt_{i}', vtype='c', lb=0) 
        # at what time is i picked up from MCd:
        pt[I_dict.get(i)] = model.addVar(name=f'pt_{I_dict.get(i)}', vtype='c', lb=0) 
        for r in range(allowed_routes): 
            # is route r dropping off patient i at their drop off node ip (=1) or not (=0):
            d[I_dict.get(i),r] = model.addVar(name=f'd_{I_dict.get(i)}_{r}', vtype='b') 
            # is route r picking up patient i at their pickup node i (=1) or not (=0):
            p[i,r] = model.addVar(name=f'p_{i}_{r}', vtype='b') 
    
    
    for l in I0:
        if allow_wait_patients:
            # how long does patient l have to wait at MC:
            wait_at_MC_before[l] = model.addVar(name=f'wait_at_MC_before_{l}', vtype='c', lb=0)
            wait_at_MC_after[l] = model.addVar(name=f'wait_at_MC_after_{l}', vtype='c', lb=0)
         

    if allow_delay_clients:
        for i in (I1 + I2 + I3):
            # how long is the delay of staff s at client i for service start:
            delay_at_client[i] = model.addVar(name=f'service_delay_{i}', vtype='c', lb=0) 

    for c in range(number_of_vehicles):
        # is car c used (=1) or not (=0):
        use_car[c] = model.addVar(name=f'use_car_{c}', vtype='b') 
        # at what time does car c start its travel for the day:
        start_car_travel[c] = model.addVar(name=f'start_car_travel_{c}', vtype='c', lb=0)
        # at what time does car c end its travel for the day: 
        end_car_travel[c] = model.addVar(name=f'end_car_travel_{c}', vtype='c', lb=0)
        # what is the operating time of car c for the day:
        car_travel[c] = model.addVar(name=f'car_travel_{c}', vtype='c', lb=0)
        for r in range(allowed_routes):
            # does car c drive route r (=1) or not (=0):
            route_car_match[c,r] = model.addVar(name=f'route_{r}_done_by_car_{c}', vtype='b') 
    
    if allow_overtime:
        for s in staff: 
            overtime[s] = model.addVar(name=f'overtime_{s}', vtype='c', lb=0, ub=120)

    for i in I_total:
        if i == 'MC':
            for r in range(allowed_routes):
                capacity_used[i,r] = model.addVar(name=f'capacity_used_{i}_{r}', vtype='I', lb=0, ub=vehicle_capacity)
        elif i != 'MCd':
            capacity_used[i] = model.addVar(name=f'capacity_used_{i}', vtype='I', lb=0, ub=vehicle_capacity)

    for r in range(allowed_routes): 
        route_len[r] = model.addVar(name=f'route_len_{r}', vtype='c', lb=0)

    
    """---------------------------------------------------------------------------------------------------------------------"""
    """---------------------------------------------------------------------------------------------------------------------"""
    """---------------------------------------------------------------------------------------------------------------------"""
    """Setting Constraints"""
    
    """Using Knowledge from Staff Schedule"""
    for s in staff:
        # extract schedule of staff s
        staff_schedule = client_staff_match[s]
        # how many clients does s have?
        number_of_clients = len(staff_schedule)
        for i in range(number_of_clients-1):
            # set current client
            c = staff_schedule[i]
            k = staff_schedule[i+1]
            model.addConstr(Pt[I_dict.get(c),s] <= Dt[k,s])
            # some route r has to bring s from cp to k
            model.addConstrs(P[I_dict.get(c),s,r] == D[k,s,r] for r in range(allowed_routes))
            

    """Flow Conservation, Making sure every node is visited and SEC"""
    for r in range(allowed_routes):
        # no incoming arcs to the depot start node
        model.addConstr(quicksum(X[j,'MC',r] for j in I_total if j != 'MC') == 0)
        # no outgoing arcs from depot end node
        model.addConstr(quicksum(X['MCd',j,r] for j in I_total if j != 'MCd') == 0)
        # exactly one outgoing arc from depot start node
        model.addConstr(quicksum(X['MC',j,r] for j in I_total if j !=  'MC') == 1)
        # exactly one incoming arc to depot end node
        model.addConstr(quicksum(X[j,'MCd',r] for j in I_total if j != 'MCd') == 1)
        for i in I_total:
            for j in I_total:
                if (i != j) & ((i,j) != ('MC', 'MCd')):
                    # allow for routes not to be used by travelling from MC to MCd
                    # in that case, no other edge can be used on that route
                    # necessary? Doesn't SEC already prevent subtours? and there is no other possibility than a subtour to have the solver cheat, right?
                    model.addConstr(1 - X['MC', 'MCd',r] >= X[i,j,r])

    for i in I_total:
        if (i != 'MC') & (i != 'MCd'):
            # every node i has to be visited exactly once by the sum of all routes
            model.addConstr(quicksum(X[i,j,r] for r in range(allowed_routes) for j in I_total if j != i) == 1)  
            for r in range(allowed_routes):
                # every route r has to leave a node i as many times as it enters the node i
                model.addConstr(quicksum(X[i,j,r] for j in I_total if j != i) == quicksum(X[j,i,r] for j in I_total if j != i)) 


    """Time windows, Pick up and Drop off of the staff at clients (Home Health Care Problem)"""
    # for i in (I1 + I2 + I3):
    #     model.addConstr(quicksum(W[i,s] for s in S if (i,s) in node_staff_tuple) == 1)
    
    for (i,s) in node_staff_tuple:
        if i != 'MCd':
            # if the respective staff s is serving client i, it has to be dropped off by some route r:
            model.addConstr(quicksum(D[i,s,r] for r in range(allowed_routes)) == 1) 
            # if the respective staff s has been dropped off at client i, it needs to be picked up by some route r from the partner node ip:
            model.addConstr(quicksum(P[I_dict.get(i),s,r] for r in range(allowed_routes)) == 1)
            for r in range(allowed_routes):
                # the drop off time of the respective staff s has to be equal to the arrival time of the route r at that respective drop off node i:
                model.addConstr((1 - D[i,s,r]) * M + Dt[i,s] >= t[i,r]) 
                model.addConstr(Dt[i,s] <= (1 - D[i,s,r]) * M + t[i,r])
                # the pick up time of the respective staff s has to be equal to the arrival time of the picking up route r at the respective node:
                model.addConstr(Pt[I_dict.get(i),s] <= (1 - P[I_dict.get(i),s,r]) * M + t[I_dict.get(i),r]) 
                model.addConstr((1 - P[I_dict.get(i),s,r]) * M + Pt[I_dict.get(i),s] >= t[I_dict.get(i),r])

    for i in I_total:
        for j in I_total:
            if i != j:
                for r in range(allowed_routes):
                    # if route r goes from i to j, the arrival time at j has to be larger or equal than the arrival time at i plus the travel time inbetween: MTZ-subtour elimination
                    model.addConstr((1 - X[i,j,r]) * M + t[j,r] >= t[i,r] + int(tt.get(i).get(j))) 


    if allow_overtime:
        # limit working hours of nurses to eight hours, additional time is overtime:
        model.addConstr(Dt['MCd',s] - Pt['MC',s] <= 480 + overtime[s])  
    else:
        # limit working hours of nurses to eight hours:
        model.addConstr(Dt['MCd',s] - Pt['MC',s] <= 480)    
    for s in staff: 
        # every staff s can be at most on one route r and if so s needs to be picked up at MC:
        model.addConstr(quicksum(P['MC',s,r] for r in range(allowed_routes)) <= 1) 
        # if staff s is picked up, s also needs to be dropped off at MCd:
        model.addConstr(quicksum(P['MC',s,r] for r in range(allowed_routes)) == quicksum(D['MCd',s,r] for r in range(allowed_routes)))
        # staff s is always first picked up from MC before it can be dropped at MCd in the end:
        model.addConstr(Pt['MC',s] <= Dt['MCd',s])
        for r in range(allowed_routes):
            # set the drop off time at MC_ (equivalent to end of work):
            model.addConstr((1 - D['MCd',s,r]) * M + Dt['MCd',s] >= t['MCd',r]) 
            # set the pick up time at MC (equivalent to start of work):
            model.addConstr(Pt['MC',s] <= t['MC',r] + (1 - P['MC',s,r]) * M) 

    if allow_delay_clients:
        # set the delay of staff s at the client i with respect to the latest allowed starting time:
        model.addConstrs(int(LST_client.get(i)) >= Dt[i,s] - delay_at_client[i] for (i,s) in node_staff_tuple if i != 'MCd')
    else:
        # ensure that the latest allowed starting time is always respected:
        model.addConstrs(int(LST_client.get(i)) >= Dt[i,s] for (i,s) in node_staff_tuple if i != 'MCd')
    if allow_wait_staff:
        # keep track of how long staff s has to wait a client i before s can begin the service:
        model.addConstrs(int(EST_client.get(i)) <= Dt[i,s] + wait_at_client_before[i,s] for (i,s) in node_staff_tuple if i != 'MCd')
        # difference between drop off time at client node i and pick up time at client partner node ip equals
        # the service duration plus the time s had to wait before and after the service:
        model.addConstrs(Pt[I_dict.get(i),s] - Dt[i,s] == int(STD_client.get(i)) + wait_at_client_before[i,s] + wait_at_client_after[i,s] for (i,s) in node_staff_tuple if i != 'MCd')
        # every nurse can wait at most one hour a day:
        model.addConstrs(quicksum(wait_at_client_before[i,s] + wait_at_client_after[i,s] for i in I_total if (i,s) in node_staff_tuple) <= max_wait_staff for s in staff) 
    else:
        # ensure that the earliest allowed starting time is always respected:
        model.addConstrs(int(EST_client.get(i)) <= Dt[i,s] for (i,s) in node_staff_tuple if i != 'MCd')
        # difference between drop off time at client node i and pick up time at client partner node ip has to be
        # larger or equal to the standard service time:
        model.addConstrs(Pt[I_dict.get(i),s] -  Dt[i,s] >= int(STD_client.get(i)) for (i,s) in node_staff_tuple if i != 'MCd')

    for (i,s) in node_staff_tuple:
        # if staff is dropped off at node i it has to be picked up at the respective pickup node ip:
        model.addConstr(quicksum(D[i,s,r] for r in range(allowed_routes)) == quicksum(P[I_dict.get(i),s,r] for r in range(allowed_routes))) 
        # only if the staff started at MC it can be sent to other nodes:
        model.addConstr(quicksum(P['MC',s,r] for r in range(allowed_routes)) >= quicksum(D[i,s,r] for r in range(allowed_routes)))
        # drop off time at MCd must be larger or equal than any pickup time of the staff (just making sure, the solver is not cheating):
        model.addConstr(Dt['MCd',s] >= Pt[I_dict.get(i),s])
        # similarly the pickup time at MC must be smaller or equal to any drop off time of the staff
        model.addConstr(Pt['MC',s] <= Dt[i,s])
       
    for i in (I0 + I1 + I2 + I3):
        for r in range(allowed_routes):
            model.addConstr(X[i,I_dict.get(i),r] == 0)
    
    # Force only one time variable per node to take a value larger 0: NECCESSARY anymore???
    for i in I_total:
        if (i != 'MC') & (i != 'MCd'):
            model.addConstr(quicksum(y[i,r] for r in range(allowed_routes)) == 1) # jeder Knoten genau einmal angefahren
            for r in range(allowed_routes):
                model.addConstr(t[i,r] <= M * y[i,r])
                # model.addConstr(t[i,r] <= M * quicksum(X[i,j,r] for j in I_total if i!=j))
           
    for r in range(allowed_routes):
        for s in staff:
            # every staff s that has been picked up by a route r has to be dropped off by the same route r
            model.addConstr(
                quicksum(P[I_dict.get(i),s,r] for i in I_total if (i,s) in node_staff_tuple) 
                == quicksum(D[i,s,r] for i in I_total if (i,s) in node_staff_tuple)
                )


    """Dial a ride section"""
    for i in I0:
        # every patient i needs to be picked up from home by a route r:
        model.addConstr(quicksum(p[i,r] for r in range(allowed_routes)) == 1) 
        for r in range(allowed_routes):
            # patient i can only be picked up on a route r that is going by his house:
            model.addConstr(p[i,r] <= quicksum(X[i,j,r] for j in I_total if i != j)) 
    for i in I_0: 
        # every patient i needs to be dropped off at home by a route r:
        model.addConstr(quicksum(d[i,r] for r in range(allowed_routes)) == 1) 
        for r in range(allowed_routes):
            # patient i can only be dropped off by a route r that is going by his house:
            model.addConstr(d[i,r] <= quicksum(X[i,j,r] for j in I_total if i != j)) 
    for r in range(allowed_routes):
        for i in I0:
            # if r is the picking up patient, the drop off time at MC corresponds to the arrival time of r at node MCd:
            model.addConstr(dt[i] >= t['MCd',r] - (1 - p[i,r]) * M) 
            model.addConstr(dt[i] <= t['MCd',r] + (1 - p[i,r]) * M) 
            # if r is dropping off patient, the pick up time at MC corresponds to the leaving time of r at node MC:
            model.addConstr(pt[I0_dict.get(i)] <= t['MC',r] + (1 - d[I0_dict.get(i),r]) * M) 
            model.addConstr(pt[I0_dict.get(i)] >= t['MC',r] - (1 - d[I0_dict.get(i),r]) * M)
    if allow_wait_patients:
        for i in I0:
            # respect time that it takes to process patient at MC:
            model.addConstr(int(STD_patient.get(i)) + wait_at_MC_after[i] + wait_at_MC_before[i] == pt[I0_dict.get(i)] - dt[i])
            # respect earliest starting time at MC (including waiting):
            model.addConstr(int(EST_patient.get(i)) <= dt[i] + wait_at_MC_before[i])
            # limit waiting time of patient i at MC to an hour:
            model.addConstr(wait_at_MC_before[i] + wait_at_MC_after[i] <= max_wait_patiens)
    else:
            for i in I0:
                # alternative without punishing wait time at MC:
                model.addConstr(int(STD_patient.get(i)) <= pt[I0_dict.get(i)] - dt[i])
                # respect earliest starting time at MC (without waiting):
                model.addConstr(int(EST_patient.get(i)) <= dt[i]) 
    for i in I0:
        # respect latest starting time at MC:
        model.addConstr(int(LST_patient.get(i)) >= dt[i])
        
 

    """Vehicle Capacity Constraint"""


    for i in I_total:
        if (i != 'MCd') and (i != 'MC'):
            for j in I_total:
                if (j != 'MCd') and (j != i) and (j != 'MC'):
                    model.addConstr(capacity_used[j] >= capacity_used[i] 
                                    + quicksum(P[j,s,r] for r in range(allowed_routes) for s in staff if (find_key(j, I_dict),s) in node_staff_tuple) 
                                    - quicksum(D[j,s,r] for r in range(allowed_routes) for s in staff if (j,s) in node_staff_tuple)
                                    #+ quicksum(op[i,j,l,r] for r in range(allowed_routes) for l in I0)
                                    + quicksum(p[j,r] for r in range(allowed_routes) if j in I0)
                                    - quicksum(d[j,r] for r in range(allowed_routes) if j in I_0)
                                    + (quicksum(X[i,j,r] for r in range(allowed_routes)) - 1) * 10 # big M
                                    )
                    model.addConstr(capacity_used[j] <= capacity_used[i] 
                                    + quicksum(P[j,s,r] for r in range(allowed_routes) for s in staff if (find_key(j, I_dict),s) in node_staff_tuple) 
                                    - quicksum(D[j,s,r] for r in range(allowed_routes) for s in staff if (j,s) in node_staff_tuple)
                                    #+ quicksum(op[i,j,l,r] for r in range(allowed_routes) for l in I0)
                                    + quicksum(p[j,r] for r in range(allowed_routes) if j in I0)
                                    - quicksum(d[j,r] for r in range(allowed_routes) if j in I_0)
                                    - (quicksum(X[i,j,r] for r in range(allowed_routes)) - 1) * 10
                                    )

    for j in I_total:
        if (j != 'MCd') and (j != 'MC'):
            for r in range(allowed_routes):
                model.addConstr(capacity_used[j] >= capacity_used['MC',r] 
                                + quicksum(P[j,s,r] for s in staff if (find_key(j, I_dict),s) in node_staff_tuple) 
                                - quicksum(D[j,s,r] for s in staff if (j,s) in node_staff_tuple)
                                #+ quicksum(op[i,j,l,r] for r in range(allowed_routes) for l in I0)
                                + quicksum(p[j,r] for i in range(1) if j in I0)
                                - quicksum(d[j,r] for i in range(1) if j if j in I_0)
                                + (X['MC',j,r] - 1) * 10
                                )
                model.addConstr(capacity_used[j] <= capacity_used['MC',r] 
                                + quicksum(P[j,s,r] for s in staff if (find_key(j, I_dict),s) in node_staff_tuple) 
                                - quicksum(D[j,s,r] for s in staff if (j,s) in node_staff_tuple)
                                #+ quicksum(op[i,j,l,r] for r in range(allowed_routes) for l in I0)
                                + quicksum(p[j,r] for i in range(1) if j in I0)
                                - quicksum(d[j,r] for i in range(1) if j if j in I_0)
                                - (X['MC',j,r] - 1) * 10
                                )
                    
    for r in range(allowed_routes): # einsammeln und absetzen der patienten anpassen, auch dass verschiedene routen 
        #  model.addConstr(capacity_used['MC',r] == quicksum(P['MC',s,r] for s in staff) + quicksum(op['MC',j,l,r] for l in I0))
        model.addConstr(capacity_used['MC',r] == quicksum(P['MC',s,r] for s in staff) + quicksum(d[i,r] for i in I_0))


    """Counting vehicles in parallel use"""  
    ## increases computational complexity by factor > 6
    # have increasing number of routes be equal to increasing time of leaving the depot: --> avoid symmetry (reduced computation time by roughly factor 5)
    for r1 in range(allowed_routes):
        for r2 in range(r1 + 1, allowed_routes):
            model.addConstr(predecessor[r1,r2] == 1)
            model.addConstr(predecessor[r2,r1] == 0)
    # if route r1 starts before route r2, and route r1 and route r2 are both performed on the same car c then route r1 has to end before route r2 starts:
    for r1 in range(allowed_routes):
        for r2 in range(allowed_routes):
            if r1 != r2:
                for c in range(number_of_vehicles):
                    model.addConstr(t['MCd', r1] <= t['MC', r2] + M * (3 - route_car_match[c,r1] - route_car_match[c,r2] - predecessor[r1,r2]))
    # only if a car c is being used, route r can be performed by it:
    for c in range(number_of_vehicles):
        for r in range(allowed_routes):
            model.addConstr(use_car[c] >= route_car_match[c,r]) 
    # avoid symmetry:
    for c1 in range(number_of_vehicles):
        for c2 in range(number_of_vehicles):
            if c2 > c1:
                model.addConstr(use_car[c1] >= use_car[c2])
    # every route has to be served by a car:
    for r in range(allowed_routes):
        model.addConstr(quicksum(route_car_match[c,r] for c in range(number_of_vehicles)) == 1)
    # # link binary car use variable to the number of cars being used:
    # model.addConstr(quicksum(use_car[c] for c in range(number_of_vehicles)) == cars_used)
    # set start und end time for specific car, as well es limit to one driver driving time
    for c in range(number_of_vehicles):
        model.addConstr(car_travel[c] == end_car_travel[c] - start_car_travel[c])
        model.addConstr(car_travel[c] <= 480)
        for r in range(allowed_routes):
            model.addConstr(start_car_travel[c] <= (1 - route_car_match[c,r]) * M + t['MC',r])
            model.addConstr((1 - route_car_match[c,r]) * M + end_car_travel[c] >= t['MCd',r])

    for r in range(allowed_routes):
        model.addConstr(route_len[r] >= t['MCd',r] - t['MC',r])
    

    """---------------------------------------------------------------------------------------------------------------------"""
    """---------------------------------------------------------------------------------------------------------------------"""
    """---------------------------------------------------------------------------------------------------------------------"""
    """Optimization"""
    if allow_delay_clients and allow_overtime:
        model.setObjective(
            quicksum(use_car[c] for c in range(number_of_vehicles)) * (driver + car_fixed)  # fixed cost for car being used plus driver 8h shift
            + len(staff1) * level_1 + len(staff2) * level_2 + len(staff3) * level_3         # cost for nurses 8h shifts
            + quicksum(route_len[r] for r in range(allowed_routes)) * fuel_cost             # cost for fuel
            + quicksum(overtime[s] for s in staff1) * (level_1/8 + over_time)/60            # cost for overtime (per minte)
            + quicksum(overtime[s] for s in staff2) * (level_2/8 + over_time)/60 
            + quicksum(overtime[s] for s in staff3) * (level_3/8 + over_time)/60
            + quicksum(delay_at_client[i] for i in (I1 + I2 + I3)) * 20/60                  # penalty cost for being late --> integrate in main
            )
    elif (not allow_delay_clients) and allow_overtime:
        model.setObjective(
            quicksum(use_car[c] for c in range(number_of_vehicles)) * (driver + car_fixed)  # fixed cost for car being used plus driver 8h shift
            + len(staff1) * level_1 + len(staff2) * level_2 + len(staff3) * level_3         # cost for nurses 8h shifts
            + quicksum(route_len[r] for r in range(allowed_routes)) * fuel_cost             # cost for fuel
            + quicksum(overtime[s] for s in staff1) * (level_1/8 + over_time)/60            # cost for overtime (per minte)
            + quicksum(overtime[s] for s in staff2) * (level_2/8 + over_time)/60 
            + quicksum(overtime[s] for s in staff3) * (level_3/8 + over_time)/60
            )
    elif allow_delay_clients and (not allow_overtime):
        model.setObjective(
            quicksum(use_car[c] for c in range(number_of_vehicles)) * (driver + car_fixed)  # fixed cost for car being used plus driver 8h shift
            + len(staff1) * level_1 + len(staff2) * level_2 + len(staff3) * level_3         # cost for nurses 8h shifts
            + quicksum(route_len[r] for r in range(allowed_routes)) * fuel_cost             # cost for fuel
            + quicksum(delay_at_client[i] for i in (I1 + I2 + I3)) * 20/60                  # penalty cost for being late
            )
    else:
        model.setObjective(
            quicksum(use_car[c] for c in range(number_of_vehicles)) * (driver + car_fixed)  # fixed cost for car being used plus driver 8h shift
            + len(staff1) * level_1 + len(staff2) * level_2 + len(staff3) * level_3         # cost for nurses 8h shifts
            # + quicksum(route_len[r] for r in range(allowed_routes)) * fuel_cost             # cost for fuel
            )
    # log_callback = LogCallback()
    model.setParam(GRB.Param.TimeLimit, 3600)
    # model.setParam(GRB.Param.SolutionLimit, 25)
    model.setParam(GRB.Param.MIPFocus, 1)
    model.update()
    # model.Params.TuneTimeLimit = 3600
    # model.tune()
    # model.optimize(LogCallback.__call__(log_callback, model, GRB.Callback.MIP))
    model.optimize()

    """Output"""
    if model.SolCount > 0:
    
        """Derive Staff Schedules"""
        for s in staff:
            data = {'Current Node': [],
                  'Next Node': [],
                  'Time': [],
                  'Drop off?': [],
                  'EST': [],
                  'LST': [],
                  'Task duration': [],
                  'Pick up?': [],
                  'Route:': [],
                  }
            file_name = f'outputs/schedule_staff_{s}.xlsx'
            df = pd.DataFrame(data)
            output_file_path = f'schedule_{s}'
            schedule = client_staff_match.get(s)
            counter = 0
            found = False
            for j in I_total:
                if j != 'MC':
                    for r in range(allowed_routes):
                        if (round(X['MC',j,r].getAttr('X')) == 1) and (round(P['MC',s,r].getAttr('X') == 1)):
                            new_row =   {'Current Node': 'MC',
                                        'Next Node': j,
                                        'Time': round(t['MC',r].getAttr('X')),
                                        'Drop off?': 'no',
                                        'EST': 'n.a.',
                                        'LST': 'n.a.',
                                        'Task duration': 'n.a.',
                                        'Pick up?': 'yes',
                                        'Route:': r,
                                        }
                            i = j
                            found = True
                            break
                if found:
                    break
            connect_df = pd.DataFrame([new_row])
            df = pd.concat([df, connect_df])
            if i == schedule[counter]:
                counter += 1
                new_row =   {'Current Node': i,
                            'Next Node': I_dict.get(i),
                            'Time': round(t[i,r].getAttr('X')),
                            'Drop off?': 'yes',
                            'EST': EST_client.get(i),
                            'LST': LST_client.get(i),
                            'Task duration': STD_client.get(i),
                            'Pick up?': 'no',
                            'Route:': 'working',
                            }
                i = I_dict.get(i)
            else:
                for j in I_total: 
                    if i != j:
                        if round(X[i,j,r].getAttr('X')) == 1:
                            new_row =   {'Current Node': i,
                                        'Next Node': j,
                                        'Time': round(t[i,r].getAttr('X')),
                                        'Drop off?': 'no',
                                        'EST': 'n.a.',
                                        'LST': 'n.a.',
                                        'Task duration': 'n.a.',
                                        'Pick up?': 'no',
                                        'Route:': r,
                                        }
                            i = j
            connect_df = pd.DataFrame([new_row])
            df = pd.concat([df, connect_df])
            resume = True
            while resume:
                if counter < len(schedule):
                    if find_key(i, I_dict) in schedule:
                        found = False
                        for r in range(allowed_routes):
                            if round(P[i,s,r].getAttr('X')) == 1:
                                for j in I_total: 
                                    if i != j:
                                        if round(X[i,j,r].getAttr('X')) == 1:
                                            new_row =   {'Current Node': i,
                                                        'Next Node': j,
                                                        'Time': round(t[i,r].getAttr('X')),
                                                        'Drop off?': 'no',
                                                        'EST': 'n.a.',
                                                        'LST': 'n.a.',
                                                        'Task duration': 'n.a.',
                                                        'Pick up?': 'yes',
                                                        'Route:': r,
                                                        }
                                            i = j
                                            found = True
                                            break
                            if found:
                                break
                    elif i == 'MCd':
                        new_row =   {'Current Node': i,
                                        'Next Node': 'n.a.',
                                        'Time': round(t[i,r].getAttr('X')),
                                        'Drop off?': 'yes',
                                        'EST': 'n.a.',
                                        'LST': 'n.a.',
                                        'Task duration': 'n.a.',
                                        'Pick up?': 'no',
                                        'Route:': r,
                                        }
                        resume = False
                    elif i == schedule[counter]:
                        for r in range(allowed_routes):
                            if sum(round(X[j,i,r].getAttr('X')) for j in I_total if j != i) == 1:
                                break
                        counter += 1
                        new_row =   {'Current Node': i,
                                    'Next Node': I_dict.get(i),
                                    'Time': round(t[i,r].getAttr('X')),
                                    'Drop off?': 'yes',
                                    'EST': EST_client.get(i),
                                    'LST': LST_client.get(i),
                                    'Task duration': STD_client.get(i),
                                    'Pick up?': 'no',
                                    'Route:': 'working',
                                    }
                        i = I_dict.get(i)
                    else: 
                        found = False
                        for r in range(allowed_routes):
                            for j in I_total: 
                                if i != j:
                                    if round(X[i,j,r].getAttr('X')) == 1:
                                        new_row =   {'Current Node': i,
                                                    'Next Node': j,
                                                    'Time': round(t[i,r].getAttr('X')),
                                                    'Drop off?': 'no',
                                                    'EST': 'n.a.',
                                                    'LST': 'n.a.',
                                                    'Task duration': 'n.a.',
                                                    'Pick up?': 'no',
                                                    'Route:': r,
                                                    }
                                        i = j
                                        found = True
                                        break
                            if found:
                                break
                else:
                    if i == 'MCd':
                        new_row =   {'Current Node': i,
                                    'Next Node': 'n.a.',
                                    'Time': round(t[i,r].getAttr('X')),
                                    'Drop off?': 'yes',
                                    'EST': 'n.a.',
                                    'LST': 'n.a.',
                                    'Task duration': 'n.a.',
                                    'Pick up?': 'no',
                                    'Route:': r,
                                    }
                        resume = False
                    elif find_key(i, I_dict) in schedule:
                        found = False
                        for r in range(allowed_routes):
                            if round(P[i,s,r].getAttr('X')) == 1:
                                for j in I_total: 
                                    if i != j:
                                        if round(X[i,j,r].getAttr('X')) == 1:
                                            new_row =   {'Current Node': i,
                                                        'Next Node': j,
                                                        'Time': round(t[i,r].getAttr('X')),
                                                        'Drop off?': 'no',
                                                        'EST': 'n.a.',
                                                        'LST': 'n.a.',
                                                        'Task duration': 'n.a.',
                                                        'Pick up?': 'yes',
                                                        'Route:': r,
                                                        }
                                            i = j
                                            found = True
                                            break
                            if found:
                                    break

                    else: 
                        for r in range(allowed_routes):
                            for j in I_total: 
                                if i != j:
                                    if round(X[i,j,r].getAttr('X')) == 1:
                                        new_row =   {'Current Node': i,
                                                    'Next Node': j,
                                                    'Time': round(t[i,r].getAttr('X')),
                                                    'Drop off?': 'no',
                                                    'EST': 'n.a.',
                                                    'LST': 'n.a.',
                                                    'Task duration': 'n.a.',
                                                    'Pick up?': 'no',
                                                    'Route:': r,
                                                    }
                                        i = j
                                        break

                connect_df = pd.DataFrame([new_row])
                df = pd.concat([df, connect_df])
            # sort entries by time
            df_sorted = df.sort_values(by='Time')
            df_sorted.set_index(['Time'], inplace=True)

            # save output to excel file
            df_sorted.to_excel(file_name, engine='openpyxl')
            workbook = oxl.load_workbook(file_name)
            worksheet = workbook.active

            # adjust column witdh and center entries
            for col in worksheet.columns:
                max_length = 0
                column = col[0].column_letter  # Get the column name
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                adjusted_width = (max_length + 2)  # Extra space for better readability
                worksheet.column_dimensions[column].width = adjusted_width
            workbook.save(file_name)
    

        
        """Derive Car Schedule"""
        for c in range(number_of_vehicles):
            if round(use_car[c].getAttr('X')) == 0:
                pass
            else: 
                file_name = f'outputs/schedule_car_{c}.xlsx'
                data = {'Current Node': [],
                        'Next Node': [],
                        'Time': [],
                        'Used Capacity (leaving the node)': [],
                        'Route': [],
                        'Node Type': [],
                        }
                df = pd.DataFrame(data)
                for r in range(allowed_routes):
                    if round(X['MC','MCd',r].getAttr('X')) == 0:
                        if round(route_car_match[c,r].getAttr('X')) == 1:
                            new_row =   {'Current Node': 'MCd',
                                        'Next Node': 'n.a.',
                                        'Time': round(t['MCd',r].getAttr('X')),
                                        'Used Capacity (leaving the node)': 'n.a.',
                                        'Route': r,
                                        'Node Type': 'end of route'
                                        }
                            connect_df = pd.DataFrame([new_row])
                            df = pd.concat([df, connect_df])
                            for i in I_total: 
                                for j in I_total:
                                    if i != j:
                                        if round(X[i,j,r].getAttr('X')) == 1:
                                            if i != 'MC':
                                                node_type = 'error'
                                                if i in I1:
                                                    node_type = 'type 1 drop off'
                                                elif i in I2:
                                                    node_type = 'type 2 drop off'
                                                elif i in I3: 
                                                    node_type = 'type 3 drop off'
                                                elif i in I0:
                                                    node_type = 'patient pickup'
                                                elif i in I_1:
                                                    node_type = 'type 1 pick up'
                                                elif i in I_2:
                                                    node_type = 'type 2 pick up'
                                                elif i in I_3:
                                                    node_type = 'type 3 pick up'
                                                elif i in I_0:
                                                    node_type = 'patient drop off'
                                                new_row =   {'Current Node': i,
                                                            'Next Node': j,
                                                            'Time': round(t[i,r].getAttr('X')),
                                                            'Used Capacity (leaving the node)': round(capacity_used[i].getAttr('X')),
                                                            'Route': r,
                                                            'Node Type': node_type
                                                            }
                                            else: 
                                                new_row =   {'Current Node': i,
                                                            'Next Node': j,
                                                            'Time': round(t[i,r].getAttr('X')),
                                                            'Used Capacity (leaving the node)': round(capacity_used['MC',r].getAttr('X')),
                                                            'Route': r,
                                                            'Node Type': 'start of route'
                                                            }
                                            connect_df = pd.DataFrame([new_row])
                                            df = pd.concat([df, connect_df])
                # sort entries by time 
                df_sorted = df.sort_values(by='Time')
                df_sorted.set_index(['Time'], inplace=True)
                # save output to excel file
                df_sorted.to_excel(file_name, engine='openpyxl')
                workbook = oxl.load_workbook(file_name)
                worksheet = workbook.active

                # adjust column witdh and center entries
                for col in worksheet.columns:
                    max_length = 0
                    column = col[0].column_letter  # Get the column name
                    for cell in col:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(cell.value)
                        except:
                            pass
                        cell.alignment = Alignment(horizontal='center', vertical='center')
                    adjusted_width = (max_length + 2)  # Extra space for better readability
                    worksheet.column_dimensions[column].width = adjusted_width
                workbook.save(file_name)

                        

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

        arcs = []
        for i in I_total:
            for j in I_total:
                if i != j:
                    for r in range(allowed_routes):
                        if X[i,j,r].getAttr('X') >= 0.99:
                            arcs += [(i,j,r)]
        node_info = {'MC': '',
                     'MCd': '',
                     }
        for i in I_total:
            if (i != 'MC') & (i != 'MCd'):
                for s in staff:
                    if (i,s) in node_staff_tuple:
                        if Dt[i,s].getAttr('X') > 0.01:
                            node_info[i] = np.round(Dt[i,s].getAttr('X'), 0)
                        if Pt[I_dict.get(i),s].getAttr('X') > 0.01:
                            node_info[I_dict.get(i)] = np.round(Pt[I_dict.get(i),s].getAttr('X'), 0)

        return model.SolCount, arcs, node_info
    elif model.Status == GRB.TIME_LIMIT:
        print(f"Optimization stopped, because Time Limit is reached. Optimilaity Gap: {model.MIPGap}")
        return model.Status, None, None
    elif model.Status == GRB.INFEASIBLE:
        print("Model is infeasible.")
        model.computeIIS()
        model.write("outputs/infeasibility_report.ilp")
        return model.Status, None, None
    



"""TODOs"""
    # Do we have symmetry?
    # Working hours drivers --> included
    # limit waiting time of patient --> included
    # break time of nurses
    # limit working time and unproductive time of nurses --> included
    # what is a good big M?
    # avoid staff being on two tours at the same time --> included
    # how many drivers and cars are used at the same time? Which consecutive tours could be performed by the same car, driver, nurse --> included for cars and drivers
    # retrieve the final plan for the operator
    # allow for selection and deselection of model flexibilities
    # allow for clients not to be served at all?
    # exclude edges from i to ip for faster solving?
    # compare MTZ to DFJ?


"""Create Graphs showing Nodes investigated, Open Nodes as well as Primal and Dual Bound over optimization time"""
# class LogCallback:
#     def __init__(self):
#         self.primal_bounds = []
#         self.dual_bounds = []
#         self.open_nodes = []
#         self.processed_nodes = []

#     def __call__(self, model, where):
#         if where == GRB.Callback.MIP:
#             # Get primal and dual bounds
#             primal_bound = model.cbGet(GRB.Callback.MIP_OBJBST)
#             dual_bound = model.cbGet(GRB.Callback.MIP_OBJBND)
#             # Get number of open and processed nodes
#             open_nodes = model.cbGet(GRB.Callback.MIP_NODLFT)
#             processed_nodes = model.cbGet(GRB.Callback.MIP_NODCNT)

#             # Store values
#             self.primal_bounds.append(primal_bound)
#             self.dual_bounds.append(dual_bound)
#             self.open_nodes.append(open_nodes)
#             self.processed_nodes.append(processed_nodes)


"""Tiny function to find the key of an dictionary entry"""
def find_key(value_to_find, dict):
    for key, value in dict.items():
        if value == value_to_find:
            return key
    return 'Nothing'