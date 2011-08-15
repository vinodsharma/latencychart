import signal

class TimeoutException(Exception): 
    pass 

def timeout(timeout_time, default=None):
    def timeout_function(f, *args):
         def timeout_handler(signum, frame):
             raise TimeoutException()

         old_handler = signal.signal(signal.SIGALRM, timeout_handler) 
         signal.alarm(timeout_time) # triger alarm in timeout_time seconds
         try: 
             retval = f(*args)
         except TimeoutException:
             if default:
                 return default
             else:
                 raise
         finally:
             signal.signal(signal.SIGALRM, old_handler) 
         signal.alarm(0)
         return retval
    return timeout_function
