import json
import os
import time
import psutil

class Logger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        self.log_file = os.path.join(self.log_dir, f"log_{int(time.time())}.json")
        self.log_data = {
            "task_info": {},
            "steps": [],
            "summary": {},
        }

    def log_task_info(self, objective, model):
        self.log_data["task_info"] = {
            "objective": objective,
            "model": model,
            "start_time": time.time(),
        }

    def log_step(self, operation, start_time, end_time):
        step_data = {
            "operation": operation,
            "start_time": start_time,
            "end_time": end_time,
            "duration": end_time - start_time,
            "resource_usage": self.get_resource_usage(),
        }
        self.log_data["steps"].append(step_data)

    def log_summary(self, total_time):
        self.log_data["summary"] = {
            "total_time": total_time,
            "final_resource_usage": self.get_resource_usage(),
        }
        self.write_log()

    def get_resource_usage(self):
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
        }

    def write_log(self):
        with open(self.log_file, 'w') as f:
            json.dump(self.log_data, f, indent=4)
