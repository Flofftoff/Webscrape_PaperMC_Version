from bs4 import BeautifulSoup as bs
from dotenv import load_dotenv
import os
import requests
import json
import pprint
import time


#constants
url = "https://papermc.io/downloads/paper"

load_dotenv()

web_info = os.getenv("API_KEY") 

#logging
errors_dict = {"network_error": 0, "discrepency": 0, "alert_error": 0, "successful": 0, "total_validations": 0}

data_version_old = {'latestStableVersion': "",
                    'latestExperimentalVersion': ""}

time_start = time.time()

def scrape_website(url, errors):
    while True:
        try:
            website = requests.get(url)
            break
        except requests.exceptions.ConnectionError:
            errors["network_error"] += 1
            time.sleep(5)
    scraped = bs(website.text, "html.parser")

    nextjs_script = scraped.find("script", id="__NEXT_DATA__").text.strip()
    nextjs_dict = json.loads(nextjs_script)
    data_nextjs = nextjs_dict["props"]["pageProps"]["project"]
    data_nextjs.pop("name")
    data_nextjs.pop("latestVersionGroup")

    current_version = scraped.find("span", attrs={"class": "text-blue-600"}).text.strip()

    get_experimental_version = scraped.find("button", class_=["rounded-lg", "text-red-700"])
    split_experimental_version = get_experimental_version.text.strip().split() # At the time of wrinting this, this returns: ['Toggle', 'experimental', 'builds', 'for', '1.21.5'] -> so just using [-1] at the end would remove the need for the following loop, but in case Paper decides to change its wording, there is no problem.
    for string in split_experimental_version:
        if not string.isalpha(): # Minecraft versions are always in the format of "1.*.*" therefore, we have got numbers and dots, which are not alphachars
            experimental_version = string
            break
    
    data_web = {"latestStableVersion": current_version,
                "latestExperimentalVersion": experimental_version}
    
    return(data_web, data_nextjs)

def validate_data(data_web, data_nextjs, data_version_old, errors):
    if data_web == data_nextjs:
        data_web["valid"]= True
    else:
        data_web["valid"]= False
        errors["discrepency"] += 1
   
    if data_version_old == "":
       data_version_old = data_web
    elif data_version_old["latestStableVersion"] != data_web["latestStableVersion"]:
        data_web["changed"] = "Stable"
    elif data_version_old["latestExperimentalVersion"] != data_web["latestExperimentalVersion"]:
        data_web["changed"] = "Experimental"
    else:
        data_web["changed"] = False
    errors["total_validations"] += 1
    return data_web

def trigger_Alert(data, web_info, send_Alert, errors):
    if data["changed"] == "Stable":
        priority = 9
        if not data["valid"]:
            priority = 4
        return(send_Alert(web_info, data, priority, errors))
    if data["changed"] == "Experimental":
        priority = 3
        if not data["valid"]:
            priority = 2
        return(send_Alert(web_info, data, priority, errors))

def send_Alert(web_info, data, priority, errors):
    dummy_version = "latest" + data["changed"] + "Version"
    content = {
       "content": f"@everyone Paper Version {data[dummy_version]} ({data['changed']}) ist da",
       "username": "Karbonat Erold",  # Optional custom name for the bot
       "embeds": [  # You can also add more details as an embed
           {
               "title": f"Paper Version {data[dummy_version]} ({data['changed']})",
               "description": f"New Paper version {data[dummy_version]} is now available in the {data['changed']} channel!",
               "color": 5620992  # Optional: set embed color
           }
       ]
    }
    while True:
        try:
            requests.post(web_info, json=content)
            errors["successful"] +=1
            break
        except requests.exceptions.ConnectionError:
            errors["alert_error"] += 1
            time.sleep(5)

try:
    while True:
        print("Start: ", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        scraped_data, script_data = scrape_website(url, errors_dict)
        print("1: ", scraped_data, f"\n", script_data)
        validated_data = validate_data(scraped_data, script_data, data_version_old, errors_dict)
        print("2: ", validated_data)
        data_version_old = validated_data
        trigger_Alert(validated_data, web_info, send_Alert, errors_dict)
        print("3: Valiation complete, waiting for 60sec")
        time.sleep(60)
        print("4: restarting")
except KeyboardInterrupt:
    print("\n⛔ Interrupted by user. Cleaning up...")

finally:
    time_end = time.time()
    runtime = time_end - time_start
    runtime_dict = {"Seconds": runtime,
               "Minutes": runtime/60,
               "Hours": runtime/(60*60),
               "Days": runtime/(60*60*24)
               }
    print(pprint.pformat(errors_dict))
    print(pprint.pformat(runtime_dict))
