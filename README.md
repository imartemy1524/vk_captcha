# [vk_captcha](https://github.com/imartemy1524/vk_captcha) - solve vk captcha free for 60% accuracy
### Fast examples:</h3>
#### using [vk_api](https://github.com/python273/vk_api) library:
```python
from vk_captcha import vk_api_handler
vk = vk_api_handler.VkApiCaptcha("88005553535", "efwoewkofokw")  # this login will create captcha
vk_api_handler.Solver.logging = True  # enable logging
vk.auth() # getting captcha error and automatically solve it
```
#### another way with [vk_api](https://github.com/python273/vk_api):
```python
from vk_captcha import VkCaptchaSolver
from vk_api import VkApi
solver = VkCaptchaSolver(logging=True)  # use logging=False on deploy
vk = VkApi(login='...', password='...', captcha_handler=solver.vk_api_captcha_handler)
vk.method("any.method.with.captcha.will.be.handled")
```
#### just solve captcha from *url* / *bytes*
```python
from vk_captcha import VkCaptchaSolver
import random, requests

session = requests.Session()  
session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'

solver = VkCaptchaSolver(logging=True)  # use logging=False on deploy
sid = random.randint(122112, 10102012012012)
easy_captcha = False
url = f"https://api.vk.com/captcha.php?sid={sid}&s={int(easy_captcha)}"

answer, accuracy = solver.solve(
    url=url,
    minimum_accuracy=0.33,  # keep solving captcha while accuracy < 0.33
    repeat_count=14,  # if we solved captcha with less than minimum_accuracy, then retry repeat_count times
    session=session  # optional parameter. Useful if we want to use proxy or specific headers
)
# or
#answer, accuracy = solver.solve(bytes_data=session.get(url))
print(f"I solved captcha = {answer} with accuracy {accuracy:.4}")
```
#### async way:
```python
from vk_captcha import VkCaptchaSolver
import random, asyncio
solver = VkCaptchaSolver(logging=True)  # use logging=False on deploy
async def captcha_solver():
    sid = random.randint(122112, 10102012012012)
    easy_captcha = False
    url = f"https://api.vk.com/captcha.php?sid={sid}&s={int(easy_captcha)}"
    answer, accuracy = await solver.solve_async(url=url, minimum_accuracy=0.4, repeat_count=10)
    print(f"Solved captcha = {answer} with accuracy {accuracy:.4}")
asyncio.run(captcha_solver())
```

In theory, you can use command line solver:
```commandline
python -m vk_captcha -url "https://api.vk.com/captcha.php?sid=2323832899382092" -minimum-accuracy 0.33 -repeat-count 13
```
