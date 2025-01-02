import gurobipy as gp
from gurobipy import GRB
import matplotlib.pyplot as plt
class LogCallback:
    def __init__(self):
        self.primal_bounds = []
        self.dual_bounds = []
        self.open_nodes = []
        self.processed_nodes = []

    def __call__(self, model, where):
        if where == GRB.Callback.MIP:
            # Get primal and dual bounds
            primal_bound = model.cbGet(GRB.Callback.MIP_OBJBST)
            dual_bound = model.cbGet(GRB.Callback.MIP_OBJBND)
            # Get number of open and processed nodes
            open_nodes = model.cbGet(GRB.Callback.MIP_NODLFT)
            processed_nodes = model.cbGet(GRB.Callback.MIP_NODCNT)

            # Store values
            self.primal_bounds.append(primal_bound)
            self.dual_bounds.append(dual_bound)
            self.open_nodes.append(open_nodes)
            self.processed_nodes.append(processed_nodes)
def log_plotter(log_callback):           
    # Plot primal and dual bounds
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.plot(log_callback.primal_bounds, label='Primal Bound')
    plt.plot(log_callback.dual_bounds, label='Dual Bound')
    plt.xlabel('Iterations')
    plt.ylabel('Bound Value')
    plt.legend()
    plt.title('Primal and Dual Bounds')

    # Plot processed and open nodes
    plt.subplot(1, 2, 2)
    plt.plot(log_callback.processed_nodes, label='Processed Nodes')
    plt.plot(log_callback.open_nodes, label='Open Nodes')
    plt.xlabel('Iterations')
    plt.ylabel('Node Count')
    plt.legend()
    plt.title('Processed and Open Nodes')

    plt.tight_layout()
    plt.show()