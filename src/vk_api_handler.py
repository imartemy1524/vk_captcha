import vk_api
from .solver import VkCaptchaSolver
Solver = VkCaptchaSolver()
class VkApiCaptcha(vk_api.VkApi):
    def captcha_handler(self, captcha):
        return Solver.vk_api_captcha_handler(captcha)
