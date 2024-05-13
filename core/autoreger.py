import asyncio
import random
import time
from asyncio import Semaphore, sleep, create_task, gather

from core.utils import logger
from core.utils.file_to_list import file_to_list
from core.gmnetwork import GmNetwork

from inputs.config import (
    THREADS, CUSTOM_DELAY, KEYS_FILE_PATH, PROXIES_FILE_PATH, INVITES_FILE_PATH
)


class AutoReger:
    def __init__(self):
        self.success = 0
        self.custom_user_delay = None

    @staticmethod
    def get_accounts():
        keys = file_to_list(KEYS_FILE_PATH)
        proxies = file_to_list(PROXIES_FILE_PATH)
        

        if not (min_accounts_len := len(keys)):
            logger.info(f"keys.txt is empty!")
            return

        accounts = []

        for i in range(min_accounts_len):
            accounts.append((
                keys[i],
                proxies[i] if len(proxies) > i else None,
             ))

        return accounts

    async def start(self):
        self.custom_user_delay = CUSTOM_DELAY

        accounts = AutoReger.get_accounts()

        if accounts is None:
            return

        logger.info(f"Successfully grab {len(accounts)} accounts")

        semaphore = Semaphore(THREADS)

        tasks = []
        for account in accounts:
            task = create_task(self.worker(account, semaphore))
            tasks.append(task)

        await gather(* tasks)

        if self.success:
            logger.success(f"Successfully handled {self.success} accounts :)")
        else:
            logger.warning(f"No accounts handled :(")

    async def worker(self, account: tuple, semaphore: Semaphore):
        key, proxy = account
        logs = {"ok": False, "file": "fail.txt", "msg": ""}
        
        for _ in range(6):
            try:
                async with semaphore:
                    await AutoReger.custom_delay()

                    gmnet = GmNetwork(key)
                    await gmnet.define_proxy(proxy)
                    
                    if await gmnet.login():
                        data = await gmnet.get_info()
                        if data['success'] == False:
                            if data.get("error_code") == 2100:
                                logger.info("Account activation")
                                invites = file_to_list(INVITES_FILE_PATH)
                                code, agents_count = await gmnet.account_activation(random.choice(invites))
                                with open(INVITES_FILE_PATH, 'a') as ouf:        
                                    print(code, file=ouf)
                                #input()
                            else:
                                logs["msg"] = data.get("error_message")
                        else:
                            agents_count=len(data.get("result", {}).get("agent"))
                        if agents_count==0:
                            rarity,energy=await gmnet.agent_set()
                            logger.info(f"Agent created: rarity {rarity} energy {energy}")
                        task=await gmnet.task(await gmnet.task_center())
                        if task['success'] == False:
                            logs["ok"]=task.get("success")
                            logs["msg"]=task.get("error_message")
                        else:
                            logs["ok"]=task.get("success")
                            daily,total=await gmnet.user_energy()
                            logs["msg"] = f"Task complete! Daily {daily}, Total {total}"
                        await gmnet.logout()
                        break
            except Exception as e:
                logs["msg"] = str(e)
                logger.error(f"Error {e}")

        if logs["ok"]:
            logs["file"] = "success"
            
            self.success += 1


        gmnet.logs(logs["file"], logs["msg"])

    @staticmethod
    async def custom_delay():
        if CUSTOM_DELAY[1] > 0:
            sleep_time = random.uniform(CUSTOM_DELAY[0], CUSTOM_DELAY[1])
            logger.info(f"Sleep for {int(sleep_time)} seconds")
            await sleep(sleep_time)

    @staticmethod
    def is_file_empty(path: str):
        return not open(path).read().strip()