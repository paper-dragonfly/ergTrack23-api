import subprocess
import time

def execute_command(cmd, max_retries, wait_time):
    retry_count = 0

    while retry_count < max_retries:
        result = subprocess.run(cmd, shell=True)

        if result.returncode == 0:
            print(f"SUCCESS: {cmd}")
            return True
        else:
            retry_count += 1
            print(f"FAILED: {cmd}. Attempt {retry_count}/{max_retries}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

    print(f"FAILED PERMANENTLY: {cmd}")
    return False

if __name__ == "__main__":
    execute_command("alembic upgrade head", 5, 1)
