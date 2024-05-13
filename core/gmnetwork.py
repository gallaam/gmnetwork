import asyncio
import datetime
import random
import aiohttp

from aiohttp import ClientResponseError
from aiohttp_socks import ProxyType, ProxyConnector, ChainProxyConnector
from tenacity import retry, stop_after_attempt, stop_after_delay, wait_fixed

from inputs.config import MOBILE_PROXY_CHANGE_IP_LINK, MOBILE_PROXY
from .utils import Web3Utils, logger
from .utils.file_manager import str_to_file

  

class GmNetwork:
    def __init__(self, key: str, proxy: str = None):
        self.web3_utils = Web3Utils(key=key)
        # self.proxy = f'http://{proxy}' if proxy else None

        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.7',
            'Content-Type': 'application/json',
            'Origin': 'https://launchpad.gmnetwork.ai',
            'Priority': 'u=1, i',
            'Referer': 'https://launchpad.gmnetwork.ai/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }

        self.session = None
        self.proxy = proxy

    async def define_proxy(self, proxy: str):
        if MOBILE_PROXY:
            await GmNetwork.change_ip()
            self.proxy = MOBILE_PROXY

        if proxy is not None:
            self.proxy = proxy

        connector = self.proxy and ProxyConnector.from_url(f'http://{self.proxy}')
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            trust_env=True,
            connector=connector
        )

    @staticmethod
    async def change_ip():
        async with aiohttp.ClientSession() as session:
            await session.get(MOBILE_PROXY_CHANGE_IP_LINK)

    @retry(stop=stop_after_attempt(20))
    async def login(self):
        url = 'https://api-launchpad.gmnetwork.ai/user/login/'
        timestamp = GmNetwork.get_unix_timestamp()
        msg0 = f"Welcome to GM Launchpad.\nPlease sign this message to login GM Launchpad."
        msg = f"Welcome to GM Launchpad.\nPlease sign this message to login GM Launchpad.\n\nTimestamp: {timestamp}"
        sig=self.web3_utils.get_signed_code(msg)[2:]
        json_data = {
            'address': self.web3_utils.acct.address,
            'message': msg0,
            'timestamp': timestamp,
            'signature': sig,
            'login_type': 100
        }
        
        response = await self.session.post(url, json=json_data)
        res_json = await response.json()
        
        auth_token = res_json.get("result", {}).get("access_token")
        
        if auth_token:
            self.upd_login_token(auth_token)

        return bool(auth_token)

    def upd_login_token(self, token: str):
        self.session.headers["access-token"] = f"{token}"

    @retry(stop=stop_after_attempt(5))
    async def get_info(self):
        url = 'https://api-launchpad.gmnetwork.ai/user/auth/info/'
        
        response = await self.session.get(url)
        res_json = await response.json()
        
        return res_json
        
    @retry(stop=stop_after_attempt(5))
    async def account_activation(self, invite: str):
        url = 'https://api-launchpad.gmnetwork.ai/user/invite_code/'

        json_data = {
            'invite_code': invite,
            'address': self.web3_utils.acct.address
        }
        
        response = await self.session.post(url, json=json_data)
        
        res_json = await response.json()
        
        invite_code = res_json.get("result", {}).get("user_info", {}).get("invite_code")
        agents_count = len(res_json.get("result", {}).get("user_info", {}).get("agent"))
        
        return invite_code, agents_count

    @retry(stop=stop_after_attempt(5))
    async def agent_set(self):
        url = 'https://api-launchpad.gmnetwork.ai/user/auth/agent_set/'

        json_data = {
            'nft_id': '',
        }
        
        response = await self.session.post(url, json=json_data)
        
        res_json = await response.json()
        
        rarity = res_json.get("result", {}).get("rarity")
        energy = res_json.get("result", {}).get("energy")
        
        return rarity,energy
        
    @retry(stop=stop_after_attempt(5))
    async def task_center(self):
        url = 'https://api-launchpad.gmnetwork.ai/task/auth/task_center/?season_um=1'
        
        response = await self.session.get(url)
        
        res_json = await response.json()
        
        id_task = res_json.get("result", {}).get("check_in_task_info", {}).get("id")
        
        return id_task
	
    @retry(stop=stop_after_attempt(5))
    async def task(self, id: str):
        url = 'https://api-launchpad.gmnetwork.ai/task/auth/task/'

        json_data = {
            'task_id': id,
            'category': 200
        }
        
        response = await self.session.post(url, json=json_data)
        
        res_json = await response.json()
        
        return res_json

    @retry(stop=stop_after_attempt(5))
    async def user_energy(self):
        url = 'https://api-launchpad.gmnetwork.ai/energy/auth/user_energy/'
        
        response = await self.session.get(url)
        
        res_json = await response.json()
        
        daily = res_json.get("result", {}).get("daily")
        total = res_json.get("result", {}).get("total")
        
        return daily, total
    
    async def logout(self):
        await self.session.close()

    @staticmethod
    def get_current_date():
        return datetime.datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def get_unix_timestamp():
        return int(datetime.datetime.now().timestamp())
        
    @staticmethod
    def get_utc_timestamp():
        return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def logs(self, file_name: str, msg_result: str = ""):
        address = self.web3_utils.acct.address
        file_msg = f"{address}|{self.proxy}"
        str_to_file(f"./logs/{file_name}.txt", file_msg)
        msg_result = msg_result and " | " + str(msg_result)

        if file_name == "success":
            logger.success(f"{address}{msg_result}")
        else:
            logger.error(f"{address}{msg_result}")