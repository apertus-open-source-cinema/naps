import atexit
from time import time


current_task = None
current_start = None

task_timings = []

def print_task_timing(current_task, elapsed):
    print(f"🕑 {current_task} took {elapsed:.2f} s")

@atexit.register
def print_summary_at_end():
    print(f"### timing summary")
    for task_timing in task_timings:
        print_task_timing(*task_timing)



def start_task(name):
    end_task()
    print(f"\n### starting {name}")
    global current_task, current_start
    current_task = name
    current_start = time()


def end_task():
    global current_task, current_start
    if current_task is not None:
        assert current_start is not None
        task_timings.append((current_task, time() - current_start))
        print_task_timing(*task_timings[-1])
    current_task = None
    current_start = None
