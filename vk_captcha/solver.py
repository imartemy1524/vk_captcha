import concurrent.futures
import os.path
import time
import aiohttp
import asyncio

import onnxruntime as onr
import numpy as np
import requests
import cv2
import vk_api
import threading
from requests.exceptions import ProxyError
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vkbottle import CaptchaError
    from vk_wave import APIOptionsRequestContext

characters = ['z', 's', 'h', 'q', 'd', 'v', '2', '7', '8',
              'x', 'y', '5', 'e', 'a', 'u', '4', 'k', 'n', 'm', 'c', 'p']
img_width = 130
img_height = 50
lock = threading.Lock()
# you can use some existing lock for logging
logging_lock: "threading.Lock|None" = None
max_length = 7


class VkCaptchaSolver:
    """
    Vk captcha handling
    Fast examples:
1) vk_api.VkApi
>>> from vk_captcha import vk_api_handler
>>> vk = vk_api_handler.VkApiCaptcha("88005553535", "efwoewkofokw")  # this login will create captcha
>>> vk_api_handler.Solver.logging = True  # enable logging
>>> vk.auth() # getting Password Api error
2) solving captcha from url
>>> from vk_captcha import VkCaptchaSolver
>>> import random
>>> solver = VkCaptchaSolver(logging=True)
>>> captcha_response, accuracy = solver.solve(url=f"https://api.vk.com/captcha.php?sid={random.randint(0,10000000)}", minimum_accuracy=0.15)
>>> async def async_way():
... await solver.solve_async(url=f"https://api.vk.com/captcha.php?sid={random.randint(0,10000000)}")
3) if you have image in bytes:
>>> solver.solve(bytes_data=requests.get(f"https://api.vk.com/captcha.php?sid={random.randint(0,10000000)}").content)
    """
    TOTAL_COUNT = 0
    FAIL_COUNT = 1
    TOTAL_TIME = 0

    def __init__(self, logging=False, model_fname=os.path.dirname(__file__) + "/model.onnx"):
        self.logging = logging
        self.Model = onr.InferenceSession(model_fname)
        self.ModelName = self.Model.get_inputs()[0].name

    def solve(self, url=None, bytes_data=None, minimum_accuracy=0, repeat_count=10, session=None) -> 'str,float':
        """Solves VK captcha
        :param bytes_data: Raw image data
        :type bytes_data: bytes
        :param url: url of the captcha ( or pass bytes_data )
        :type url: str
        :param minimum_accuracy: Minimum accuracy of recognition.
                                 If accuracy < minimum_accuracy then download captcha again
                                 and solve it again. (Do it for repeat_count times)
                                 Works only with url passed
                                 Range = [0,1]
        :type minimum_accuracy: float
        :param repeat_count: Repeat solving count ( look at minimum_accuracy )
                                Range = [1,999]
        :type repeat_count: int
        :param session: requests.Session object or None
        :return Tuple[answer:str, accuracy:float ( Range=[0,1]) ]
        """
        if url is not None:
            url = url.replace('&resized=1', '').replace("?resized=1&", '?')
        if self.logging:
            with logging_lock:
                print(f"Solving captcha {url}")
        if repeat_count < 1:
            raise ValueError(f"Parameter repeat_count = {repeat_count} < 1")
        for i in range(repeat_count):
            if url is not None:
                for _ in range(4):
                    try:
                        bytes_data = (session or requests).get(
                            url, headers={"Content-language": "en"}).content
                        if bytes_data is None:
                            raise ProxyError(
                                "Can not download data, probably proxy error")
                        break
                    except:
                        if _ == 3:
                            raise
                        time.sleep(0.5)
            answer, accuracy = self._solve_task(bytes_data)
            if accuracy >= minimum_accuracy or url is None:
                break
            if self.logging:
                with logging_lock:
                    print(
                        f"Solved accuracy(={accuracy:.4}) < miniumum(={minimum_accuracy:.4}). Trying again.")
        with lock:
            VkCaptchaSolver.TOTAL_COUNT += 1
        return answer, accuracy

    @property
    def argv_solve_time(self):
        """Argv solve time in seconds per one captcha.
        Start returning value after first solve ( solve_async) call"""
        with lock:
            # zero division error capturing
            return VkCaptchaSolver.TOTAL_TIME / (VkCaptchaSolver.TOTAL_COUNT or 1)

    @property
    def _async_runner(self):
        if not hasattr(VkCaptchaSolver, "_runner"):
            VkCaptchaSolver._runner = concurrent.futures.ThreadPoolExecutor(
                max_workers=5
            )
        return VkCaptchaSolver._runner

    async def solve_async(self, url=None, bytes_data=None, minimum_accuracy=0, repeat_count=10, session=None) -> 'str,float':
        """Solves VK captcha async
        :param bytes_data: Raw image data
        :type bytes_data: byte
        :param url: url of the captcha ( or pass bytes_data )
        :type url: str
        :param minimum_accuracy: Minimum accuracy of recognition.
                                 If accuracy < minimum_accuracy then download captcha again
                                 and solve it again. (Do it for repeat_count times)
                                 Works only with url passed
                                 Range = [0,1]
        :type minimum_accuracy: float
        :param repeat_count: Repeat solving count ( look at minimum_accuracy )
                                Range = [1,999]
        :param session: aiohttp.ClientSession session to download captcha
        :type session: aiohttp.ClientSession
        :type repeat_count: int
        :return answer:str, accuracy:float ( Range=[0,1])
        """
        if self.logging:
            print(f"Solving captcha {url}")
        if repeat_count < 1:
            raise ValueError(f"Parameter repeat_count = {repeat_count} < 1")
        for i in range(repeat_count):
            if url is not None:
                for _ in range(4):
                    try:
                        if session is None:
                            async with aiohttp.ClientSession(headers={"Content-language": "en"}) as session_m, \
                                    session_m.get(url) as resp:
                                bytes_data = await resp.content.read()
                        else:
                            async with session.get(url) as resp:
                                bytes_data = await resp.content.read()
                        if bytes_data is None:
                            raise ProxyError(
                                "Can not download captcha - probably proxy error")
                        break
                    except Exception:
                        if _ == 3:
                            raise
                        await asyncio.sleep(0.5)
            if self.logging:
                t = time.time()
            #  running in background async
            res = asyncio.get_event_loop().run_in_executor(
                self._async_runner, self._solve_task, bytes_data)
            completed, _ = await asyncio.wait((res,))
            #  getting result
            answer, accuracy = next(iter(completed)).result()
            if accuracy >= minimum_accuracy or url is None:
                break
            print(
                f"Solved accuracy(={accuracy:.4}) < miniumum(={minimum_accuracy:.4}). Trying again.")
        with lock:
            VkCaptchaSolver.TOTAL_COUNT += 1
        return answer, accuracy

    def _solve_task(self, data_bytes: bytes):
        t = time.time()

        img = cv2.imdecode(np.asarray(
            bytearray(data_bytes), dtype=np.uint8), -1)
        img: "np.ndarray" = img.astype(np.float32) / 255.
        if img.shape != (img_height, img_width, 3):
            cv2.resize(img, (img_width, img_height))
        img = img.transpose([1, 0, 2])
        #  Creating tensor ( adding 4d dimension )
        img = np.array([img])
        # !!!HERE MAGIC COMES!!!!
        result_tensor = self.Model.run(None, {self.ModelName: img})[0]
        # decoding output
        answer, accuracy = self.get_result(result_tensor)

        delta = time.time() - t
        with lock:
            VkCaptchaSolver.TOTAL_TIME += delta
        if self.logging:
            with logging_lock:
                print(
                    f"Solved captcha = {answer} ({accuracy:.2%} {time.time() - t:.3}sec.)")

        return answer, accuracy

    async def vk_wave_captcha_handler(self, error: dict, api_ctx: 'APIOptionsRequestContext'):
        method = error["error"]["request_params"][0]["value"]
        request_params = {}
        for param in error["error"]["request_params"]:
            if param["key"] in ("oauth", "v", "method"):
                continue
            request_params[param["key"]] = param["value"]

        key = await self.solve_async(error["error"]["captcha_img"], minimum_accuracy=0.33)

        request_params.update(
            {"captcha_sid": error["error"]["captcha_sid"], "captcha_key": key})
        return await api_ctx.api_request(method, params=request_params)

    def vk_wave_attach_to_api_session(self, api_session):
        d = api_session.default_api_options.error_dispatcher
        d.add_handler(14, self.vk_wave_captcha_handler)

    @staticmethod
    def get_result(pred):
        """CTC decoder of the output tensor
        https://distill.pub/2017/ctc/
        https://en.wikipedia.org/wiki/Connectionist_temporal_classification
        :return string, float
        """
        accuracy = 1
        last = None
        ans = []
        # pred - 3d tensor, we need 2d array - first element
        for item in pred[0]:
            # get index of element with max accuracy
            char_ind = item.argmax()
            # ignore duplicates and special characters
            if char_ind != last and char_ind != 0 and char_ind != len(characters) + 1:
                # this element is a character - append it to answer
                ans.append(characters[char_ind - 1])
                # Get accuracy for current character and
                # multiply global accuracy by it
                accuracy *= item[char_ind]
            last = char_ind

        answ = "".join(ans)[:max_length]
        return answ, accuracy

    def vk_api_captcha_handler(self, captcha, minimum_accuracy=0.3, repeat_count=10):
        """vk_api.VkApi captcha handler function"""
        key, _ = self.solve(
            captcha.get_url(), minimum_accuracy=minimum_accuracy, repeat_count=repeat_count)
        try:
            ans = captcha.try_again(key)
            return ans
        except vk_api.ApiError as e:
            if e.code == vk_api.vk_api.CAPTCHA_ERROR_CODE:
                with lock:
                    VkCaptchaSolver.FAIL_COUNT += 1
            raise

    async def vkbottle_captcha_handler(self, error: "CaptchaError", **kwargs) -> str:
        if isinstance(error, Exception) and hasattr(error, 'code'):
            if error.code == 14:
                if hasattr(error, 'captcha_img'):
                    url = error.captcha_img
                if hasattr(error, 'img'):
                    url = error.img
                return (await self.solve_async(url=url, **kwargs))[0]
