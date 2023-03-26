import vk_api
from .solver import VkCaptchaSolver
class VkApiCaptcha(vk_api.VkApi):
    def __init__(self, model_fname=None, **params):
        super().__init__(**params)
        if model_fname:
            self.Solver = VkCaptchaSolver(model_fname=model_fname)
        else: self.Solver = VkCaptchaSolver()
    def captcha_handler(self, captcha):
        return self.Solver.vk_api_captcha_handler(captcha)
