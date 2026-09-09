from __future__ import annotations
import asyncio, time, re
from dataclasses import dataclass
import aiohttp
from .config import settings
from .ssl_utils import build_ssl_context

ALIASES = {
    "ERC20":"ETH", "ETHEREUM":"ETH", "ETH":"ETH",
    "TRC20":"TRX", "TRON":"TRX", "TRX":"TRX",
    "BEP20":"BSC", "BSC":"BSC", "BNBSMARTCHAIN":"BSC",
    "SOLANA":"SOL", "SOL":"SOL",
    "ARBITRUMONE":"ARBITRUM", "ARBITRUM":"ARBITRUM", "ARB":"ARBITRUM",
    "OPTIMISM":"OPTIMISM", "OP":"OPTIMISM",
    "POLYGON":"POLYGON", "MATIC":"POLYGON",
    "AVAXC":"AVAXC", "AVALANCHECCHAIN":"AVAXC",
    "TON":"TON", "THEOPENNETWORK":"TON",
    "BASE":"BASE", "SUI":"SUI", "APTOS":"APTOS", "BTC":"BTC", "LIGHTNINGNETWORK":"BTCLN", "BTCLN":"BTCLN",
}

def norm_chain(x:str) -> str:
    raw=re.sub(r"[^A-Z0-9]","",str(x or "").upper())
    for key,val in ALIASES.items():
        if key in raw: return val
    return raw

def num(x,default=None):
    try: return float(x)
    except Exception: return default

def yes(x,default=False):
    if isinstance(x,bool): return x
    if x is None: return default
    return str(x).lower() in {"true","1","yes","allowed","enable","enabled","normal"}

@dataclass
class ChainInfo:
    exchange:str
    base:str
    network:str
    raw_network:str
    contract:str
    withdraw_enabled:bool
    deposit_enabled:bool
    withdraw_fee_coin:float|None
    min_withdraw:float|None
    updated_at:float

class AssetRegistry:
    def __init__(self):
        self.data:dict[str,dict[str,list[ChainInfo]]]={}
        self.session:aiohttp.ClientSession|None=None
        self._task=None

    async def start(self):
        self.session=aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25,connect=8),connector=aiohttp.TCPConnector(ssl=build_ssl_context()))
        await self.refresh()
        self._task=asyncio.create_task(self._loop(),name="asset-registry")

    async def close(self):
        if self._task: self._task.cancel(); await asyncio.gather(self._task,return_exceptions=True)
        if self.session: await self.session.close()

    async def _json(self,url,params=None):
        assert self.session
        async with self.session.get(url,params=params,headers={"User-Agent":"ArbitrageBotV2/2.0"}) as r:
            r.raise_for_status(); return await r.json(content_type=None)

    async def _loop(self):
        while True:
            await asyncio.sleep(900)
            try: await self.refresh()
            except Exception as e: print("Asset registry refresh error:",e)

    async def refresh(self):
        jobs=[self._kucoin(),self._htx(),self._bitget()]
        results=await asyncio.gather(*jobs,return_exceptions=True)
        new={}
        for result in results:
            if isinstance(result,dict):
                for ex,coins in result.items(): new[ex]=coins
        if new: self.data.update(new)

    async def _kucoin(self):
        d=await self._json("https://api.kucoin.com/api/v3/currencies"); coins={}; now=time.time()
        for c in d.get("data",[]) if isinstance(d,dict) else []:
            base=str(c.get("currency","")).upper(); rows=[]
            for x in c.get("chains",[]) or []:
                raw=x.get("chainName") or x.get("chainId") or ""; rows.append(ChainInfo("kucoin",base,norm_chain(raw),str(raw),str(x.get("contractAddress") or "").lower(),yes(x.get("isWithdrawEnabled")),yes(x.get("isDepositEnabled")),num(x.get("withdrawalMinFee") or x.get("withdrawMinFee")),num(x.get("withdrawalMinSize") or x.get("withdrawMinSize")),now))
            if rows: coins[base]=rows
        return {"kucoin":coins}

    async def _htx(self):
        d=await self._json("https://api.huobi.pro/v2/reference/currencies",{"authorizedUser":"false"}); coins={}; now=time.time()
        for c in d.get("data",[]) if isinstance(d,dict) else []:
            base=str(c.get("currency","")).upper(); rows=[]
            for x in c.get("chains",[]) or []:
                raw=x.get("baseChainProtocol") or x.get("displayName") or x.get("baseChain") or x.get("chain") or ""
                fee_type=x.get("withdrawFeeType"); fee=num(x.get("transactFeeWithdraw"))
                if fee is None: fee=num(x.get("minTransactFeeWithdraw"))
                rows.append(ChainInfo("htx",base,norm_chain(raw),str(raw),"",str(x.get("withdrawStatus","")).lower()=="allowed",str(x.get("depositStatus","")).lower()=="allowed",fee,num(x.get("minWithdrawAmt")),now))
            if rows: coins[base]=rows
        return {"htx":coins}

    async def _bitget(self):
        d=await self._json("https://api.bitget.com/api/v2/spot/public/coins"); coins={}; now=time.time()
        for c in d.get("data",[]) if isinstance(d,dict) else []:
            base=str(c.get("coin") or c.get("coinName") or c.get("currency") or "").upper(); rows=[]
            for x in c.get("chains",[]) or c.get("chainList",[]) or []:
                raw=x.get("chain") or x.get("chainName") or x.get("network") or ""
                rows.append(ChainInfo("bitget",base,norm_chain(raw),str(raw),str(x.get("contractAddress") or x.get("contract") or "").lower(),yes(x.get("withdrawable") if "withdrawable" in x else x.get("withdrawEnable")),yes(x.get("rechargeable") if "rechargeable" in x else x.get("depositEnable")),num(x.get("withdrawFee")),num(x.get("minWithdrawAmount") or x.get("minWithdraw")),now))
            if rows: coins[base]=rows
        return {"bitget":coins}

    def route(self,base:str,buy_ex:str,sell_ex:str,qty:float,price_hint:float|None=None):
        buy=self.data.get(buy_ex,{}).get(base,[]); sell=self.data.get(sell_ex,{}).get(base,[])
        if not buy or not sell:
            return {
                "status":"unconfirmed","network":None,"withdraw_fee_coin":None,
                "withdraw_fee_known":False,"min_withdraw_known":False,"fully_verified":False,
                "fee_text":"не подтверждена","min_withdraw_text":"не подтверждён"
            }
        candidates=[]
        for b in buy:
            if not b.withdraw_enabled: continue
            for s in sell:
                if not s.deposit_enabled or not b.network or b.network!=s.network: continue
                if b.contract and s.contract and b.contract!=s.contract: continue
                contract_confirmed=bool(b.contract and s.contract and b.contract==s.contract)
                native_confirmed=bool(not b.contract and not s.contract and b.network==norm_chain(base))
                identity_confirmed=contract_confirmed or native_confirmed
                fee=b.withdraw_fee_coin
                minw=b.min_withdraw
                if minw is not None and minw>0 and qty<minw: continue
                candidates.append((identity_confirmed,fee is not None,fee,b,s))
        if not candidates:
            return {
                "status":"blocked","network":None,"withdraw_fee_coin":None,
                "withdraw_fee_known":False,"min_withdraw_known":False,"fully_verified":False,
                "fee_text":"общая доступная сеть не найдена","min_withdraw_text":"—"
            }
        candidates.sort(key=lambda z:(not z[0],not z[1],z[2] if z[2] is not None else float("inf")))
        identity_confirmed,fee_known,fee,b,s=candidates[0]
        min_known=b.min_withdraw is not None
        status="confirmed" if identity_confirmed else "network_match"
        fully_verified=bool(identity_confirmed and fee_known and min_known and b.withdraw_enabled and s.deposit_enabled)
        return {
            "status":status,"network":b.network,"withdraw_fee_coin":fee,
            "withdraw_fee_known":fee_known,"min_withdraw_known":min_known,"fully_verified":fully_verified,
            "fee_text":f"{fee:g} {base}" if fee_known else "не подтверждена",
            "min_withdraw_text":f"{b.min_withdraw:g} {base}" if min_known else "не подтверждён",
            "contract_confirmed":identity_confirmed,"identity_confirmed":identity_confirmed,
            "buy_withdraw":b.withdraw_enabled,"sell_deposit":s.deposit_enabled
        }

registry=AssetRegistry()
