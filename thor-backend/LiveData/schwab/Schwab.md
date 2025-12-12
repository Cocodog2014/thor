# Schwab Integration (LiveData.schwab)

The **Schwab** app inside LiveData handles:

- OAuth 2.0 login with Schwab
- Storage of access/refresh tokens
- A thin REST client (`SchwabTraderAPI`) for the Schwab Trading API
- HTTP endpoints to:
  - Start OAuth
  - Handle OAuth callback
  - List accounts
  - Fetch positions and balances (and publish them to Redis)
  - Return a formatted account summary for the frontend

It is intentionally **minimal and stateless**: it has **one model** (`BrokerConnection`) and otherwise treats Schwab as the system of record for positions, balances, and account details.

---

## App config

`apps.py`:

```python
class SchwabConfig(AppConfig):
    """
    Schwab OAuth and Trading API integration.

    Important: Uses label='SchwabLiveData' to maintain compatibility
    with existing database migrations from the old SchwabLiveData app.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'LiveData.schwab'
    label = 'SchwabLiveData'  # ← Keeps existing DB tables intact!
    verbose_name = 'Schwab OAuth & Trading API'
Key points:

name = 'LiveData.schwab' – Django app path.

label = 'SchwabLiveData' – preserves old migration/table names.

No startup side-effects yet; ready() is a no-op placeholder.

Model: BrokerConnection
models.py defines a reusable broker-connection model so future brokers (IBKR, etc.) can share the same storage:

```python
class BrokerConnection(models.Model):
    BROKER_SCHWAB = "SCHWAB"
    BROKER_CHOICES = [
        (BROKER_SCHWAB, "Charles Schwab"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="broker_connections",
        help_text="Thor user who owns this broker connection",
    )
    broker = models.CharField(
        max_length=32,
        choices=BROKER_CHOICES,
        default=BROKER_SCHWAB,
        help_text="Broker identifier (e.g. SCHWAB)",
    )
    access_token = models.TextField(
        help_text="Short-lived OAuth access token (typically 30 minutes)",
    )
    refresh_token = models.TextField(
        help_text="Long-lived refresh token (typically 7 days)",
    )
    access_expires_at = models.BigIntegerField(
        help_text="Unix timestamp when access token expires",
    )
    broker_account_id = models.CharField(
        max_length=64,
        blank=True,
        help_text="Primary broker account ID (if cached)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_expired(self) -> bool:
        import time
        return time.time() >= self.access_expires_at
```

Notes:

- Users can store multiple connections (one per broker) via `broker_connections`.
- The helper property `user.schwab_token` now proxies to `BrokerConnection` with broker=`SCHWAB` for backward compatibility.
- Future brokers can reuse the same model without schema changes.

Token helpers (tokens.py)
tokens.py defines helper functions for OAuth token exchange/refresh:

python
Copy code
def exchange_code_for_tokens(auth_code: str) -> Dict[str, any]:
    """
    Exchange OAuth authorization code for access/refresh tokens.
    ...
    TODO: Implement actual Schwab OAuth token exchange
    """
    # Placeholder - implement actual Schwab API call
    logger.info("Exchanging authorization code for tokens")
    ...
    raise NotImplementedError("Schwab OAuth token exchange not yet implemented")
python
Copy code
def refresh_tokens(refresh_token: str) -> Dict[str, any]:
    """
    Use refresh token to get a new access token.
    ...
    TODO: Implement actual Schwab OAuth token refresh
    """
    logger.info("Refreshing access token")
    ...
    raise NotImplementedError("Schwab OAuth token refresh not yet implemented")
python
Copy code
def get_token_expiry(expires_in: int) -> int:
    """
    Calculate Unix timestamp for when token expires.
    """
    return int(time.time()) + expires_in
Status:
The exchange/refresh functions are currently placeholders and raise NotImplementedError. They need to be wired to Schwab’s actual OAuth token endpoint.

API client: SchwabTraderAPI
services.py provides a very thin wrapper over the Schwab Trading API:

python
Copy code
class SchwabTraderAPI:
    BASE_URL = "https://api.schwabapi.com/trader/v1"
    
    def __init__(self, user):
        self.user = user
        self.token = user.schwab_token
        if self.token.is_expired:
            logger.warning(f"Access token expired")
    
    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.token.access_token}",
            "Accept": "application/json"
        }
    
    def fetch_accounts(self):
        url = f"{self.BASE_URL}/accounts"
        response = requests.get(url, headers=self._get_headers(), timeout=10)
        response.raise_for_status()
        return response.json()
    
    def fetch_account_details(self, account_hash, include_positions=True):
        url = f"{self.BASE_URL}/accounts/{account_hash}"
        params = {"fields": "positions"} if include_positions else {}
        response = requests.get(url, headers=self._get_headers(), params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def get_account_summary(self, account_hash):
        data = self.fetch_account_details(account_hash)
        acct = data.get('securitiesAccount', {})
        bal = acct.get('currentBalances', {})
        return {
            'net_liquidating_value': f"${bal.get('liquidationValue', 0):,2f}",
            'stock_buying_power': f"${bal.get('stockBuyingPower', 0):,2f}",
            'option_buying_power': f"${bal.get('optionBuyingPower', 0):,2f}",
            'day_trading_buying_power': f"${bal.get('dayTradingBuyingPower', 0):,2f}",
            'available_funds_for_trading': f"${bal.get('availableFunds', 0):,2f}",
            'long_stock_value': f"${bal.get('longMarketValue', 0):,2f}",
            'equity_percentage': f"{bal.get('equity', 0):.2f}%"
        }
Notes / TODOs:

Currently implements:

fetch_accounts()

fetch_account_details(account_hash, include_positions=True)

get_account_summary(account_hash) (returns formatted strings for UI).

fetch_positions / fetch_balances are referenced from views but not implemented yet (they will likely:

Call appropriate Schwab endpoints,

Then publish to Redis via LiveData.shared.redis_client).

HTTP Views
Overview
views.py exposes the public endpoints:

OAuth flow:

oauth_start

oauth_callback

Data endpoints:

list_accounts

get_positions

get_balances

account_summary

All views are @login_required and restricted to GET methods where appropriate.

oauth_start (GET)
Starts Schwab OAuth redirect:

python
Copy code
@login_required
@require_http_methods(["GET"])
def oauth_start(request):
    """
    Start Schwab OAuth flow.
    
    Redirects user to Schwab authorization page.
    """
    from urllib.parse import urlencode
    
    client_id = getattr(settings, 'SCHWAB_CLIENT_ID', None)
    redirect_uri = getattr(settings, 'SCHWAB_REDIRECT_URI', None)
    
    if not client_id or not redirect_uri:
        return JsonResponse({
            "error": "Schwab OAuth not configured",
            "message": "Set SCHWAB_CLIENT_ID and SCHWAB_REDIRECT_URI in settings"
        }, status=500)
    
    auth_url = "https://api.schwabapi.com/v1/oauth/authorize"
    
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'api'
    }
    
    oauth_url = f"{auth_url}?{urlencode(params)}"
    return HttpResponseRedirect(oauth_url)
Config required:

SCHWAB_CLIENT_ID

SCHWAB_REDIRECT_URI
in Django settings.

oauth_callback (GET)
Handles the OAuth redirect and saves tokens:

python
Copy code
@login_required
@require_http_methods(["GET"])
def oauth_callback(request):
    """
    Handle OAuth callback from Schwab.
    
    Exchanges authorization code for tokens and saves to database.
    """
    auth_code = request.GET.get('code')
    
    if not auth_code:
        return JsonResponse({"error": "No authorization code provided"}, status=400)
    
    try:
        token_data = exchange_code_for_tokens(auth_code)
        
        BrokerConnection.objects.update_or_create(
            user=request.user,
            defaults={
                'access_token': token_data['access_token'],
                'refresh_token': token_data['refresh_token'],
                'access_expires_at': get_token_expiry(token_data['expires_in'])
            }
        )
        
        return JsonResponse({
            "success": True,
            "message": "Schwab account connected successfully"
        })
    except NotImplementedError:
        return JsonResponse({
            "error": "Schwab OAuth not yet implemented"
        }, status=501)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
At present, this will hit the NotImplementedError from exchange_code_for_tokens until that function is completed.

list_accounts (GET)
Returns Schwab accounts for the logged-in user:

python
Copy code
@login_required
@require_http_methods(["GET"])
def list_accounts(request):
    """
    List all Schwab accounts for the authenticated user.
    """
    try:
        if not hasattr(request.user, 'schwab_token'):
            return JsonResponse({
                "error": "No Schwab account connected"
            }, status=404)
        
        api = SchwabTraderAPI(request.user)
        accounts = api.fetch_accounts()
        
        return JsonResponse({
            "accounts": accounts
        })
    except NotImplementedError:
        return JsonResponse({
            "error": "Schwab accounts API not yet implemented"
        }, status=501)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
get_positions (GET)
Fetches positions for a specific Schwab account and publishes them to Redis:

python
Copy code
@login_required
@require_http_methods(["GET"])
def get_positions(request, account_id):
    """
    Fetch positions for a specific account.
    
    Publishes positions to Redis for consumption by other apps.
    """
    try:
        if not hasattr(request.user, 'schwab_token'):
            return JsonResponse({
                "error": "No Schwab account connected"
            }, status=404)
        
        api = SchwabTraderAPI(request.user)
        api.fetch_positions(account_id)
        
        return JsonResponse({
            "success": True,
            "message": f"Positions published to Redis for account {account_id}"
        })
    except NotImplementedError:
        return JsonResponse({
            "error": "Schwab positions API not yet implemented"
        }, status=501)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
SchwabTraderAPI.fetch_positions is expected to:

Call Schwab’s positions endpoint,

Transform the response,

Publish to Redis (e.g., live_data:positions:{account_id}).

get_balances (GET)
Similar to get_positions, but for balances:

python
Copy code
@login_required
@require_http_methods(["GET"])
def get_balances(request, account_id):
    """
    Fetch balances for a specific account.
    
    Publishes balances to Redis for consumption by other apps.
    """
    try:
        if not hasattr(request.user, 'schwab_token'):
            return JsonResponse({
                "error": "No Schwab account connected"
            }, status=404)
        
        api = SchwabTraderAPI(request.user)
        api.fetch_balances(account_id)
        
        return JsonResponse({
            "success": True,
            "message": f"Balances published to Redis for account {account_id}"
        })
    except NotImplementedError:
        return JsonResponse({
            "error": "Schwab balances API not yet implemented"
        }, status=501)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
Again, fetch_balances must be implemented to publish data to Redis.

account_summary (GET)
Returns a UI-ready summary block of account balances & buying power:

python
Copy code
@login_required
@require_http_methods(["GET"])
def account_summary(request):
    """
    Get account summary for display in the frontend.
    
    Returns formatted account balance and buying power information.
    Query params:
        - account_hash: Schwab encrypted account number (optional, uses first account if omitted)
    """
    try:
        if not hasattr(request.user, 'schwab_token'):
            return JsonResponse({
                "error": "No Schwab account connected",
                "connected": False
            }, status=404)
        
        api = SchwabTraderAPI(request.user)
        
        account_hash = request.GET.get('account_hash')
        
        if not account_hash:
            accounts = api.fetch_accounts()
            if not accounts:
                return JsonResponse({
                    "error": "No Schwab accounts found"
                }, status=404)
            
            first_account = accounts[0]
            account_hash = first_account.get('hashValue')
            if not account_hash:
                return JsonResponse({
                    "error": "Unable to get account identifier"
                }, status=500)
        
        summary = api.get_account_summary(account_hash)
        
        return JsonResponse({
            "success": True,
            "account_hash": account_hash,
            "summary": summary
        })
    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "success": False
        }, status=500)
This is what your React/Thor frontend should hit to populate the Account Summary card for Schwab accounts.

URL Routes
urls.py wires everything together:

python
Copy code
app_name = 'schwab'

urlpatterns = [
    # OAuth flow
    path('oauth/start/', views.oauth_start, name='oauth_start'),
    path('oauth/callback/', views.oauth_callback, name='oauth_callback'),
    
    # Account management
    path('accounts/', views.list_accounts, name='list_accounts'),
    path('accounts/<str:account_id>/positions/', views.get_positions, name='get_positions'),
    path('accounts/<str:account_id>/balances/', views.get_balances, name='get_balances'),
    
    # Account summary for frontend
    path('account/summary/', views.account_summary, name='account_summary'),
]
Typical mount point in project-level urls.py:

python
Copy code
path('schwab/', include('LiveData.schwab.urls')),
Test Views (Dev Only)
test_views.py contains login-free test endpoints for OAuth:

oauth_start_test(request)

oauth_callback_test(request)

These are useful when you’re bootstrapping OAuth without auth, but should not be exposed in production.

How Other Apps Should Use Schwab
Typical flow:

User clicks “Connect Schwab” in Thor.

Frontend calls:

GET /schwab/oauth/start/ → redirect to Schwab login.

Schwab redirects back to:

GET /schwab/oauth/callback/?code=...

Tokens are saved in BrokerConnection for that user.

Later, the frontend:

Calls /schwab/account/summary/ to show net liq & buying power.

Calls /schwab/accounts/ to list available accounts.

Calls /schwab/accounts/<id>/positions/ and /schwab/accounts/<id>/balances/ to push data into Redis (consumed by ActAndPos, FutureTrading, etc).

TODO / Next Steps
Implement real Schwab OAuth:

exchange_code_for_tokens

refresh_tokens

Implement:

SchwabTraderAPI.fetch_positions(account_id)

SchwabTraderAPI.fetch_balances(account_id)

Both should publish results to Redis via LiveData.shared.redis_client.

Optionally:

Add endpoints for placing orders and streaming order status.

Integrate directly with ActAndPos.Account by syncing Schwab data into your internal accounts/positions.