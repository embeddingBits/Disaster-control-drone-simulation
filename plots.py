import matplotlib.pyplot as plt

def plot_results(stats):
    plt.plot(stats["time"], stats["served_users"])
    plt.xlabel("Time (s)")
    plt.ylabel("Users Served")
    plt.title("Disaster Relief Coverage Over Time")
    plt.grid()
    plt.show()

