# https://selenium-python.readthedocs.io/ for documentation
import time
from datetime import date, timedelta
from pathlib import Path
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By #(in order to look for elements)
from selenium.webdriver.common.keys import Keys #(in order to use special keys like ENTER, TAB,…)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


LOGIN = "U826727"
PW = "lkNYC20254!"
tomorrow = (date.today() + timedelta(days=1)).strftime("%m%d%Y")
DOWNLOAD_DIR = Path.home() / "Downloads"
SCRIPT_DIR = Path(__file__).resolve().parent

#keep chrome open after the program finishes
chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("detach", True)
chrome_options.add_experimental_option(
    "prefs",
    {
        "download.default_directory": str(DOWNLOAD_DIR),
        "download.prompt_for_download": False,
    },
)

driver=webdriver.Chrome(options=chrome_options)
driver.get("https://cbase.skychefs.com/Main")

driver.implicitly_wait(10)

# ==================================================
#Step 1: Login into CBASE WEB
# ==================================================

#username => OK
username_box = driver.find_element(By.ID, value="TextBoxUsername")
username_box.send_keys(LOGIN)

#PW => OK
password_box = driver.find_element(By.ID, value="TextBoxPassword")
password_box.send_keys(PW)

#Login Button => OK
login_button = driver.find_element(By.ID, value="LoginButton")
login_button.click()
time.sleep(3)

# ==================================================
#Step 2: Get tomorrow's flight list and enter the item list
# ==================================================

#Open Bulk Browser => OK
bulk_browser = driver.find_element(By.XPATH, value='//*[@id="bulkBrowser"]/a')
bulk_browser.click()
time.sleep(2)

#Change Date 
WebDriverWait(driver, 20).until(
    EC.frame_to_be_available_and_switch_to_it(
        (By.ID, "mainiframe")
    )
)
date_field = driver.find_element(
    By.ID,
    "ContentPlaceHolder1_TextBoxDepartureFrom"
)
date_field.clear()
date_field.send_keys(tomorrow)

#Create flight list
refresh_button = driver.find_element(By.XPATH, value='//*[@id="tabs-1"]/div/div[1]/div[3]/button')
refresh_button.click()
time.sleep(2)

#Select all flights
flight_checkmark = driver.find_element(By.XPATH, value='//*[@id="nactionrow"]/label')
flight_checkmark.click()

#Switch to Explosion Item Lists ab
explosion_list = driver.find_element(By.XPATH, value='//*[@id="tabs"]/ul/li[2]')
explosion_list.click()
time.sleep(5)

# ==================================================
#Step 3: Get Hot Food items
# ==================================================

# The production-group controls are in the third iframe nested inside mainiframe.
WebDriverWait(driver, 10).until(
    lambda d: len(d.find_elements(By.TAG_NAME, "iframe")) > 2
)
driver.switch_to.frame(driver.find_elements(By.TAG_NAME, "iframe")[2])

production_group = WebDriverWait(driver, 10).until(
    EC.visibility_of_element_located(
        (By.ID, "ContentPlaceHolder1_TextBoxProductionGroup")
    )
)

print(production_group.get_attribute("value"))

#Verify that the current selection is HOT FOOD ALL, or something else
if production_group.get_attribute("value").strip() != "HOT FOOD ALL":
    production_group.click()

    hot_food_radio = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.ID, "ContentPlaceHolder1_RadioButtonListProductionGroups_11")
        )
    )
    hot_food_label = driver.find_element(
        By.CSS_SELECTOR,
        'label[for="ContentPlaceHolder1_RadioButtonListProductionGroups_11"]'
    )
    hot_food_label.click()

    if not hot_food_radio.is_selected():
        driver.execute_script("arguments[0].click();", hot_food_radio)

    WebDriverWait(driver, 10).until(
        lambda d: d.find_element(
            By.ID, "ContentPlaceHolder1_RadioButtonListProductionGroups_11"
        ).is_selected()
    )

    production_group_ok = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, '//b[contains(@class, "popupButton") and contains(@onclick, "getSelectedProductionGroup") and .//img[@alt="ok"]]')
        )
    )
    production_group_ok.click()

    WebDriverWait(driver, 10).until(
        lambda d: d.find_element(
            By.ID, "ContentPlaceHolder1_TextBoxProductionGroup"
        ).get_attribute("value").strip() == "HOT FOOD ALL"
    )


# ==================================================
#Step 4: Export the data
# ==================================================
#Click export
export_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, '//*[@id="form1"]/div[4]/div[1]/div[3]/button')
        )
    )

export_button.click()

#Save the report in the right directory
existing_downloads = {path.name for path in DOWNLOAD_DIR.glob("*.xlsx")}
downloaded_report = WebDriverWait(driver, 120).until(
    lambda _: next(
        (
            path
            for path in DOWNLOAD_DIR.glob("*.xlsx")
            if path.name not in existing_downloads
            and not path.with_name(path.name + ".crdownload").exists()
        ),
        False,
    )
)
report_copy = SCRIPT_DIR / "bulk" / f"{tomorrow}_bulk_report.xlsx"
shutil.copy2(downloaded_report, report_copy)
print(f"Report copied to: {report_copy}")

# ==================================================
#Step 5: Logout & Close
# ==================================================
driver.switch_to.default_content()
logout_link = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable(
        (By.XPATH, '//a[@onclick="doLogout();"]')
    )
)
logout_link.click()
# driver.quit() #Closes the browser, preferred

# driver.close() #Closes the tab
