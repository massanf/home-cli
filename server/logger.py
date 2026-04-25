import queue
from collections import deque
from datetime import datetime

_logs = deque(maxlen=200)
_subscribers: list[queue.Queue] = []


def log_request(method, url, payload=None, status=None, response=None):
    entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "method": method,
        "url": url,
        "payload": payload,
        "status": status,
        "response": response,
    }
    _logs.appendleft(entry)
    for q in _subscribers:
        q.put(entry)


def get_logs():
    return list(_logs)


def subscribe():
    q = queue.Queue()
    _subscribers.append(q)
    return q


def unsubscribe(q):
    _subscribers.remove(q)
