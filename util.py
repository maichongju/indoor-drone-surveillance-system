import threading
def print_thread(name: str):
    print(f"{name} thread: {threading.get_ident()}")