from time import monotonic as time


class Empty(Exception):
    pass


class Queue:
    def __init__(self):
        self._queue = []

    def enqueue(self, item):
        self._queue.append(item)

    def dequeue(self, time_out=None):

        if time_out is not None:
            start_time = time.time()
            while self.is_empty():
                if time.time() - start_time > time_out:
                    raise Empty('Queue is empty')

        if self.is_empty():
            raise Empty('Queue is empty')
        return self._queue.pop(0)

    def peek(self, time_out=None):
        if time_out is not None:
            start_time = time()
            while self.is_empty():
                if time() - start_time > time_out:
                    raise Empty('Queue is empty')
        if self.is_empty():
            raise Empty('Queue is empty')
        return self._queue[0]

    def is_empty(self):
        return len(self._queue) == 0

    def clear(self):
        self._queue.clear()


class PriorityQueue(Queue):
    """
    Smaller number has higher priority
    """

    def __init__(self):
        super().__init__()
        self._priority_index = -1

    def enqueue(self, item):
        if self.is_empty():
            self._priority_index = 0
            self._queue.append(item)
        else:
            if item < self._queue[self._priority_index]:
                self._priority_index = len(self._queue)
            self._queue.append(item)

    def dequeue(self, time_out=None):
        # if time_out is not None:
        #     start_time = time.time()
        #     while self.is_empty():
        #         if time.time() - start_time > time_out:
        #             raise Empty('Queue is empty')

        if self.is_empty():
            raise Empty('Queue is empty')

        item = self._queue.pop(self._priority_index)
        self._update_priority_index()
        return item

    def peek(self, time_out=None):
        # if time_out is not None:
        #     end_time = time() + time_out
        #     while self.is_empty():
        #         remaining = end_time - time()
        #         if remaining <= 0.0:
        #             raise Empty('Queue is empty')
        # else:
        if self.is_empty():
            raise Empty('Queue is empty')
        return self._queue[self._priority_index]

    def _update_priority_index(self):
        if self.is_empty():
            self._priority_index = -1
        else:
            self._priority_index = self._queue.index(min(self._queue))

    def clear(self):
        super().clear()
        self._priority_index = -1