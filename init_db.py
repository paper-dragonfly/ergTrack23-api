import subprocess
import time

def execute_command(cmd, max_retries, wait_time):
    retry_count = 0

    while retry_count < max_retries:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"SUCCESS: {cmd}")
            return True
        else:
            retry_count += 1
            print(f"FAILED, RETRYING: {cmd}\n {result.stderr})
            time.sleep(wait_time)

    print(f"FAILED PERMANENTLY: {cmd}\n {result.stderr})
    return False

if __name__ == "__main__":
    execute_command("alembic upgrade head", 5, 1)
