"""
Test model in RL

"""
import traceback

import vk_api.exceptions

import vk_captcha.vk_api_handler

print("!!Crack started!!")
vk = vk_captcha.vk_api_handler.VkApiCaptcha(login='88005553535', password='abccba')
try:
    vk.auth()
except vk_api.exceptions.BadPassword as e:
    print("Successfully cracked the captcha!!!")
except Exception as e:
    print("Oops... Captcha didn't passed :(")
    traceback.print_exc()
