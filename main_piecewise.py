from data import get_data
import staff_schedule 
import routes 
from plot_graph import plotter
from gurobipy import *

"""Parameter Setting Section"""

#data set size:
data_size = 3

# available nurses (staff):
staff1 = 5
staff2 = 5
staff3 = 5

# number of vehicles and vehicle capacity:
vehicle_capacity = 4
number_of_vehicles = 6

# set of Booleans that are used to turn on and off specific constraints:
allow_wait_staff = False
allow_delay_clients = False
allow_wait_patients = False
allow_overtime = False
max_wait_staff = 60
max_wait_patients = 60
 
# staff cost per qualification, overtime wage, driver cost, driver overtime wage, fixed cost car, fuel cost car:
level_1 = 200   # 25€/h
level_2 = 240   # 30€/h
level_3 = 280   # 35€/h
over_time = 20   # 20€/h overtime surplus 
driver = 160    # 20€/h
car_fixed = 50  
fuel_cost = 25/60 * 8/100 * 1.8 # 25 km/h average speed --> 25/60 km/min, 8 l / 100 km fuel economy in city traffic, 1.8 € per liter average price




S1 = []
S2 = []
S3 = []
for s in range(staff1):
    S1 += [f's{s+1}']
for s in range(staff2):
    S2 += [f's{staff1 + s+1}']
for s in range(staff3):
    S3 += [f's{staff1 + staff2 + s+1}']
S = S1 + S2 + S3
allowed_routes = 4 * number_of_vehicles 


# import data:
I_total, I0, I_0, I1, I_1, I2, I_2, I3, I_3, tt, EST_patient, LST_patient, STD_patient, EST_client, LST_client, STD_client= get_data(f'data/data_{data_size}.xlsx')

try:

    client_staff_match = staff_schedule.solve(I1, I2, I3, EST_client, LST_client, STD_client, S, S1, S2, S3)
    print('Staff schedule done')
    model_sol, arcs, node_info = routes.solve(I_total, I0, I_0, I1, I_1, I2, I_2, I3, I_3, tt, EST_patient, LST_patient, STD_patient, EST_client, LST_client, STD_client, S1, S2, S3, vehicle_capacity, number_of_vehicles, allowed_routes, allow_wait_staff, allow_delay_clients, allow_wait_patients, allow_overtime, max_wait_staff, max_wait_patients, client_staff_match, level_1, level_2, level_3, over_time, driver, car_fixed, fuel_cost)
    # if optimal, plot the resulting graph:
    if model_sol > 0:
        plotter(arcs, node_info, I_total, allowed_routes)
except TypeError as e:
    print(e)