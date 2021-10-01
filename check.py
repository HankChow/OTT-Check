#!/usr/bin/env python3

import json
import re
from sre_constants import FAILURE
import requests
from requests import exceptions


class OTTCheck(object):

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36"
    dalvik_user_agent = "Dalvik/2.1.0 (Linux; U; Android 9; ALP-AL00 Build/HUAWEIALP-AL00)"
    default_timeout = 10
    cookie_file = None

    def __init__(self):
        pass

    def get_cookie_file_line(self, line):
        if not self.cookie_file:
            cookie_file = requests.get("https://raw.githubusercontent.com/lmc999/RegionRestrictionCheck/main/cookies", timeout=self.default_timeout).text.split("\n")
            self.cookie_file = cookie_file
        return self.cookie_file[line - 1]

    def multination(self):
        print("Netflix -> {result}".format(result=self.check_netflix()))
        print("Dazn -> {result}".format(result=self.check_dazn()))
        print("DisneyPlus -> {result}".format(result=self.check_disneyplus()))
        print("Hotstar -> {result}".format(result=self.check_hotstar()))
        print("YouTube Premium -> {result}".format(result=self.check_youtube_premium()))
        print("Amazon Prime Video -> {result}".format(result=self.check_prime_video()))

    def north_america(self):
        print("Fox -> {result}".format(result=self.check_fox()))
        print("HBO Now -> {result}".format(result=self.check_hbo_now()))
        print("HBO Max -> {result}".format(result=self.check_hbo_max()))
        print("Fubo TV -> {result}".format(result=self.check_fubo_tv()))
        print("Sling TV -> {result}".format(result=self.check_sling_tv()))
        print("Pluto TV -> {result}".format(result=self.check_pluto_tv()))

    def europe(self):
        print("Sky Go -> {result}".format(result=self.check_sky_go()))
        print("Channel 4 -> {result}".format(result=self.check_channel_4()))
        print("ITV Hub -> {result}".format(result=self.check_itv_hub()))

    def check_dazn(self):
        result = None
        response = None
        try:
            response = requests.post("https://startup.core.indazn.com/misl/v5/Startup", headers={
                "Content-Type": "application/json"
            }, data=json.dumps({
                "LandingPageKey": "generic",
                "Languages": "zh-CN,zh,en",
                "Platform": "web",
                "PlatformAttributes": {},
                "Manufacturer": "",
                "PromoCode": "",
                "Version": "2"
            }), timeout=self.default_timeout)
        except requests.exceptions.ConnectTimeout as e:
            result = "Failed (Network Connection)"
            return result
        response_json = response.json()
        if response_json["Region"].get("isAllowed") == True:
            result = "Yes (Region: {region})".format(region=response_json["Region"]["Country"].upper())
        elif response_json["Region"].get("isAllowed") == False:
            result = "No"
        else:
            result = "Unsupport"
        return result

    def check_hotstar(self):
        result = None
        status_code = None
        try:
            status_code = requests.get("https://api.hotstar.com/o/v1/page/1557?offset=0&size=20&tao=0&tas=20", headers={
                "User-Agent": self.user_agent
            }, timeout=self.default_timeout, verify=False).status_code
        except requests.exceptions.ConnectTimeout as e:
            result = "Failed (Network Connection)"
            return result
        if status_code == 401:
            region_headers = requests.head("https://www.hotstar.com", headers={
                "User-Agent": self.user_agent
            }, verify=False).headers
            region = None
            for cookie in region_headers["Set-Cookie"].split(";"):
                if re.search("geo=[A-Z]{2}", cookie):
                    region = re.search("geo=[A-Z]{2}", cookie).group()[-2:]
                    break
            site_region_url = requests.get("https://www.hotstar.com", timeout=self.default_timeout, verify=False).url
            site_region = None
            for index, _ in enumerate(site_region_url.split("/")):
                if ".com" in _:
                    site_region = site_region_url.split("/")[index + 1].upper()
                    break
            if region and (region == site_region):
                result = "Yes (Region: {region})".format(region=region)
            else:
                result = "No"
        elif status_code == 475:
            result = "No"
        else:
            result = "Failed"
        return result

    def check_disneyplus(self):
        basic_auth = "Bearer ZGlzbmV5JmJyb3dzZXImMS4wLjA.Cu56AgSfBTDag5NiRA81oLHkDZfu5L3CKadnefEAY84"
        result = None
        disney_cookie_urlencoded = self.get_cookie_file_line(1)
        disney_cookie = {_.split("=")[0]: _.split("=")[1] for _ in requests.utils.unquote(disney_cookie_urlencoded).split("&")}
        token_content = requests.post("https://global.edge.bamgrid.com/token", headers={
            "authorization": basic_auth,
            "User-Agent": self.user_agent
        }, data=disney_cookie, timeout=self.default_timeout)
        if ("forbidden-location" in token_content.text) or ("403 ERROR" in token_content.text): # need refinement: using json
            result = "No"
            return result
        refresh_token = token_content.json().get("refresh_token")
        fake_content = self.get_cookie_file_line(8)
        disney_content = fake_content.replace("ILOVEDISNEY", refresh_token)
        preview_check = requests.get("https://disneyplus.com").url
        is_unavailable = ("unavailble" in preview_check)
        try:
            response = requests.post("https://disney.api.edge.bamgrid.com/graph/v1/device/graphql", headers={
                "authorization": basic_auth,
                "User-Agent": self.user_agent
            }, data=disney_content, timeout=self.default_timeout)
        except requests.exceptions.ConnectTimeout as e:
            result = "Failed (Network Connection)"
            return result
        response_json = response.json()
        region = response_json["extensions"]["sdk"]["session"]["location"]["countryCode"]
        in_supported_location = response_json["extensions"]["sdk"]["session"]["inSupportedLocation"]
        if region == "JP":
            result = "Yes (Region: JP)"
        elif (region and not in_supported_location and not is_unavailable):
            result = "Available For [Disney+ {region}] Soon".format(region=region)
        elif (region and is_unavailable):
            result = "No"
        elif (region and in_supported_location):
            result = "Yes (Region: {region})".format(region=region)
        elif not region:
            result = "No"
        else:
            result = "Failed"
        return result

    def check_netflix(self):
        result = None
        status_code = None
        try:
            status_code = requests.get("https://www.netflix.com/title/81215567", headers={
                "User-Agent": self.user_agent
            }, timeout=self.default_timeout).status_code
        except requests.exceptions.ConnectTimeout as e:
            result = "Failed (Network Connection)"
            return result
        if status_code == 404:
            result = "Originals Only"
        elif status_code == 403:
            result = "No"
        elif status_code == 200:
            region_url = requests.get("https://www.netflix.com/title/80018499", headers={
                "User-Agent": self.user_agent
            }, timeout=self.default_timeout, allow_redirects=False).headers.get("location")
            region = region_url.split("/")[3].split("-")[0].upper() if region_url else "US"
            result = "Yes (Region: {region})".format(region=region)
        else:
            result = "Failed (Network Connection)"
        return result

    def check_youtube_premium(self):
        result = None
        response = None
        try:
            response = requests.get("https://www.youtube.com/premium", headers={
                "Accept-Language": "en"
            }).text
        except requests.exceptions.ConnectTimeout as e:
            result = "Failed (Network Connection)"
            return result
        region = re.search(r'"countryCode":"[A-Z]{2}"', requests.get("https://www.youtube.com/premium", headers={
            "User-Agent": self.user_agent,
        }, timeout=self.default_timeout).text)
        if not region:
            region = "CN" if "www.google.cn" in response else "US"
        else:
            region = region.group().split('"')[3]
        if "Premium is not available in your country" in response:
            result = "No (Region: {region})".format(region=region)
            return result
        if "YouTube and YouTube Music ad-free" in response:
            result = "Yes (Region: {region})".format(region=region)
        else:
            result = "Failed"
        return result

    def check_prime_video(self):
        result = None
        response = None
        try:
            response = requests.get("https://www.primevideo.com", headers={
                "User-Agent": self.user_agent
            }, timeout=self.default_timeout, verify=False).text
        except requests.exceptions.ConnectTimeout as e:
            result = "Failed (Network Connection)"
            return result
        region = re.search(r'"currentTerritory":"[A-Z]{2}"', response)
        if region:
            region = region.group().split('"')[3]
            result = "Yes (Region: {region})".format(region=region)
        else:
            result = "Unsupported"
        return result
       
    def check_fox(self): # TODO: test
        result = None
        response = None
        status_code = None
        try:
            response = requests.get("https://x-live-fox-stgec.uplynk.com/ausw/slices/8d1/d8e6eec26bf544f084bad49a7fa2eac5/8d1de292bcc943a6b886d029e6c0dc87/G00000000.ts?pbs=c61e60ee63ce43359679fb9f65d21564&cloud=aws&si=0", timeout=self.default_timeout, verify=False)
        except requests.exceptions.ConnectTimeout as e:
            result = "Failed (Network connection)"
        status_code = response.status_code
        if status_code == 200:
            result = "Yes"
        elif status_code == 403:
            result = "No"
        else:
            failed_result = response.text
            result = "Failed (Unexpected result: {failed_result})".format(failed_result=failed_result)
        return result

    def check_hbo_now(self): # TODO: test
        result = None
        try:
            redirect_url = requests.get("https://play.hbonow.com/", headers={
                "User-Agent": self.user_agent
            }, timeout=self.default_timeout).url
        except requests.exceptions.ConnectTimeout as e:
            result = "Failed (Network Connection)"
            return result
        if redirect_url in ["https://play.hbonow.com", "https://play.hbonow.com/"]:
            result = "Yes"
        elif redirect_url in ["http://hbogeo.cust.footprint.net/hbonow/geo.html", "http://geocust.hbonow.com/hbonow/geo.html"]:
            result = "No"
        else:
            result = "Failed (Network Connection)"
        return result
            
    def check_hbo_max(self): # TODO: test
        result = None
        try:
            redirect_url = requests.get("https://www.hbomax.com/", timeout=self.default_timeout, verify=False).url
        except requests.exceptions.ConnectTimeout as e:
            result = "Failed (Network Connection)"
            return result
        is_unavailable = "geo-availability" in redirect_url
        region = redirect_url.split("/")[3].upper() if len(redirect_url.split("/")) > 3 else None
        if is_unavailable:
            result = "No"
        elif region:
            result = "Yes (Region: {region})".format(region=region)
        else:
            result = "Yes"
        return result

    def check_fubo_tv(self): # TODO: test
        result = None
        response = None
        try:
            response = requests.get("https://www.fubo.tv/welcome", timeout=self.default_timeout, verify=False).text
        except requests.exceptions.ConnectTimeout as e:
            result = "Failed (Network Connection)"
            return result
        region = re.search('"countryCode":"\w+"', response).group().split('"')[3]
        result = (region == "USA")
        return result

    def check_sling_tv(self): # TODO: test
        result = None
        status_code = None
        try:
            status_code = requests.get("https://www.sling.com/", headers={
                "User-Agent": self.dalvik_user_agent
            }, verify=False, timeout=self.default_timeout).status_code
        except requests.exceptions.ConnectTimeout as e:
            result = "Failed (Network Connection)"
            return result
        if status_code == 200:
            result = "Yes"
        elif status_code == 403:
            result = "No"
        else:
            result = "Failed (Unexpected result: {status_code})".format(status_code=status_code)
        return result

    def check_pluto_tv(self): # TODO: test
        result = None
        redirect_url = None
        try:
            redirect_url = requests.get("https://pluto.tv/", verify=False, timeout=self.default_timeout).url
        except requests.exceptions.ConnectTimeout as e:
            result = "Failed (Network Connection)"
            return result
        if "thanks-for-watching" in redirect_url:
            result = "No"
        else:
            result = "Yes"
        return result

    def check_sky_go(self): # TODO: test
        result = None
        response = None
        try:
            response = requests.get("https://skyid.sky.com/authorise/skygo?response_type=token&client_id=sky&appearance=compact&redirect_uri=skygo://auth", verify=False, timeout=self.default_timeout)
        except requests.exceptions.ConnectTimeout as e:
            result = "Failed (Network Connection)"
            return result
        if "You don't have permission to access" in response:
            result = "No"
        else:
            result = "Yes"
        return result

    def check_channel_4(self): # TODO: test
        result = None
        response = None
        try:
            response = requests.get("https://ais.channel4.com/simulcast/C4?client=c4", verify=False, timeout=self.default_timeout)
        except requests.exceptions.ConnectTimeout as e:
            result = "Failed (Network Connection)"
            return result
        status = re.search(r'status="[A-Z]+"', response)
        if status:
            if "ERROR" in status.group():
                result = "No"
            elif "OK" in status.group():
                result = "Yes"
            else:
                result = "Failed (Unexpected result: {status})".format(status=status.group())
        else:
            result = "Failed (Network Connection)"
        return result

    def check_itv_hub(self): # TODO: test
        result = None
        status_code = None
        try:
            status_code = requests.get("https://simulcast.itv.com/playlist/itvonline/ITV", verify=False, timeout=self.default_timeout)
        except requests.exceptions.ConnectTimeout as e:
            result = "Failed (Network Connection)"
            return result
        if status_code == 404:
            result = "Yes"
        elif status_code == 403:
            result = "No"
        else:
            result = "Failed (Unexpected result: {status_code})".format(status_code=status_code)
        return result

oc = OTTCheck()
print(oc.multination())
print(oc.north_america())
print(oc.europe())
