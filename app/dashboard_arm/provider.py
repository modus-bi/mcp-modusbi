"""GigaChat credentials and bounded provider calls for dashboard chat."""
import ssl
import time
import uuid
from email.utils import parsedate_to_datetime

import httpx


class Ledger:
    def __init__(self):
        self.values = {k: 0 for k in ("prompt_tokens", "completion_tokens", "precached_prompt_tokens", "total_tokens")}
        self.calls = 0

    def add(self, usage):
        if "total_tokens" not in usage:
            raise ValueError("API did not return total_tokens; stop rather than invent billing")
        for k in self.values:
            value = usage.get(k, 0)
            if type(value) is not int or value < 0:
                raise ValueError("Invalid usage counter: " + k)
            self.values[k] += value
        self.calls += 1

def rate_limit_delay(response,attempt):
    """Retry only an explicit REST rate limit, never an exhausted token quota."""
    if response.status_code!=429:return None
    try:body=response.json()
    except ValueError:return None
    if not isinstance(body,dict):return None
    message=str(body.get('message','')).casefold()
    if 'too many requests' not in message or any(word in message for word in ('quota','insufficient','payment','balance')):
        return None
    requested=0.0
    header=response.headers.get('Retry-After','')
    if header:
        try:requested=max(0.0,float(header))
        except ValueError:
            try:requested=max(0.0,parsedate_to_datetime(header).timestamp()-time.time())
            except (TypeError,ValueError,OverflowError):pass
    return max(30.0 if attempt==0 else 45.0,requested)


class GigaAPI:
    def __init__(self, credential, scope, ca_file=None):
        self.credential = credential.removeprefix("Basic ").strip()
        self.token, self.expires = None, 0
        self.session_id = str(uuid.uuid4())
        self.retry_events = []
        context = ssl.create_default_context()
        if ca_file:
            context.load_verify_locations(cafile=ca_file)
        self.scope = scope
        self.http = httpx.Client(verify=context, timeout=httpx.Timeout(180, connect=20), follow_redirects=False,
                                 headers={"User-Agent": "modusbi-mcp-dashboard-arm/0.1", "Accept": "application/json"})

    def request(self, method, path, **kwargs):
        if time.time() >= self.expires - 60:
            response = self.http.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={"Authorization": "Basic " + self.credential, "RqUID": str(uuid.uuid4())},
                data={"scope": self.scope})
            if response.status_code != 200:
                raise RuntimeError(f"GigaChat authorization returned HTTP {response.status_code}; no secret logged")
            auth = response.json()
            self.token = auth["access_token"]
            self.expires = auth["expires_at"]
            if self.expires > 10**11:
                self.expires /= 1000
        functions=kwargs.get('json',{}).get('functions',[])
        custom_generation=path=='chat/completions' and bool(functions) and all(f.get('name','').startswith('giga_') for f in functions)
        safe_metadata=(method.upper()=='GET' and path in {'models','balance'}) or (method.upper()=='POST' and path=='functions/validate')
        for attempt in range(3):
            try:
                response = self.http.request(method, "https://api.giga.chat/v1/" + path,
                    headers={"Authorization": "Bearer " + self.token, "X-Session-ID": self.session_id}, **kwargs)
            except (httpx.NetworkError, httpx.RemoteProtocolError, httpx.ConnectTimeout,
                    httpx.ReadTimeout, httpx.WriteTimeout) as error:
                if not (custom_generation or safe_metadata):
                    raise
                self.retry_events.append({'path':path,'error_type':type(error).__name__,'attempt':attempt+1,
                                          'usage_unknown':custom_generation,'mcp_tool_executed':False})
                if attempt<2:
                    time.sleep(attempt+1)
                    continue
                raise RuntimeError(f"GigaChat {path} transport recovery exhausted ({type(error).__name__}); no MCP tool executed") from None
            rate_delay=rate_limit_delay(response,attempt) if custom_generation or safe_metadata else None
            if rate_delay is not None:
                self.retry_events.append({'path':path,'status':429,'error_kind':'rate_limit','attempt':attempt+1,
                                          'usage_unknown':custom_generation,'mcp_tool_executed':False,
                                          'retry_delay_seconds':rate_delay,'deferred':rate_delay>60})
                if rate_delay>60:
                    raise RuntimeError(f'GigaChat {path} rate limit: server requires a longer cooldown ({rate_delay:.0f}s); no MCP tool executed')
                if attempt<2:
                    time.sleep(rate_delay)
                    continue
            if response.status_code in {502,503,504} and (custom_generation or safe_metadata):
                # A failed generation cannot execute a portal tool: only a
                # successfully returned function_call reaches the MCP executor.
                # Provider usage may still be charged; preserve balance deltas.
                self.retry_events.append({'path':path,'status':response.status_code,'attempt':attempt+1,
                                          'usage_unknown':custom_generation,'mcp_tool_executed':False})
                if attempt<2:
                    time.sleep(attempt+1)
                    continue
            if response.status_code >= 400:
                raise RuntimeError(f"GigaChat {path} returned HTTP {response.status_code}; bounded provider recovery exhausted or error not retryable")
            return response.json()

    def close(self):
        self.token = self.credential = None
        self.http.close()
