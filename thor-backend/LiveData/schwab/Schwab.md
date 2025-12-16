
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