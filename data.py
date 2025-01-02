import pandas as pd
import numpy as np
def get_data(file_name):
    # read exel as pandas df and convert into list of dicts:
    travel_time_og = pd.read_excel(file_name, 
                                sheet_name='travel time - car', 
                                header=1,
                                dtype=str
                                ) 
    travel_time_og.columns = travel_time_og.columns.astype(str)

    tt = {}
    tt = travel_time_og.to_dict(orient='records')
    tt_new = {}

    for line in tt:
        key = line.get('start')
        line.pop('start')
        tt_new[key] = line
    

    # read exel as pandas df and convert into list of dicts:
    jobs_og = pd.read_excel(file_name, 
                            sheet_name=0, 
                            dtype=str,
                            header=0,
                            usecols=[0, 1, 2, 3, 4],
    )
    jobs_patient = jobs_og.loc[jobs_og['HS'] == '0'].to_dict(orient='records')
    jobs_1 = jobs_og.loc[jobs_og['HS'] == '1'].to_dict(orient='records')
    jobs_2 = jobs_og.loc[jobs_og['HS'] == '2'].to_dict(orient='records')
    jobs_3 = jobs_og.loc[jobs_og['HS'] == '3'].to_dict(orient='records')
    jobs_client = jobs_1 + jobs_2 + jobs_3
    EST_patient = {}
    LST_patient = {}
    STD_patient = {}
    EST_client = {}
    LST_client = {}
    STD_client = {}
    I0 = []
    I_0 = []
    I1 = []
    I_1 = []
    I2 = []
    I_2 = []
    I3 = []
    I_3 = []
    
    # create dictionary within a dictionary:
    for job in jobs_patient:
        EST_patient[job.get('Customer')] = job.get('EST')
        LST_patient[job.get('Customer')] = job.get('LST')
        STD_patient[job.get('Customer')] = job.get('STD')
        I0 += [job.get('Customer')]
        job_ = job.get('Customer') + 'p'
        I_0 += [job_]
    for job in jobs_client:
        EST_client[job.get('Customer')] = job.get('EST')
        LST_client[job.get('Customer')] = job.get('LST')
        STD_client[job.get('Customer')] = job.get('STD')
    for job in jobs_1:
        I1 += [job.get('Customer')]
        job_ = job.get('Customer') + 'p'
        I_1 += [job_]
    for job in jobs_2:
        I2 += [job.get('Customer')]
        job_ = job.get('Customer') + 'p'
        I_2 += [job_]
    for job in jobs_3:
        I3 += [job.get('Customer')]
        job_ = job.get('Customer') + 'p'
        I_3 += [job_]
    I = I0 + I1 + I2 + I3 + I_0 + I_1 + I_2 + I_3
    I_total = I + ['MC'] + ['MCd']

    return I_total, I0, I_0, I1, I_1, I2, I_2, I3, I_3, tt_new, EST_patient, LST_patient, STD_patient, EST_client, LST_client, STD_client

