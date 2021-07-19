from time import time


current_task = None
current_start = None


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
        print(f"🕑 {current_task} took {(time() - current_start):.2f} s")
    current_task = None
    current_start = None