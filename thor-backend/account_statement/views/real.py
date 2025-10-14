"""
Real account specific views.

Contains views for managing real money trading accounts, including
brokerage integration, account verification, and real-money-specific features.
"""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .base import AccountOwnerMixin, AccountListView, AccountDetailView, BaseAccountViewSet
from ..models import RealAccount, BrokerageProvider


class RealAccountListView(AccountListView):
    """
    List view for real money trading accounts.
    
    Shows all real accounts belonging to the current user.
    """
    model = RealAccount
    template_name = 'account_statement/real/account_list.html'
    account_type = 'Real'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Real Money Accounts'
        context['brokerage_providers'] = BrokerageProvider.choices
        return context


class RealAccountDetailView(AccountDetailView):
    """
    Detail view for real money trading accounts.
    
    Shows detailed information about a specific real account
    including verification status, API integration, and risk management.
    """
    model = RealAccount
    template_name = 'account_statement/real/account_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Real Account - {self.object.account_number}'
        context['risk_status'] = self.object.get_risk_status()
        context['can_sync'] = self.object.api_enabled
        context['verification_required'] = not self.object.is_verified
        return context


class RealAccountCreateView(AccountOwnerMixin, CreateView):
    """
    Create view for real money trading accounts.
    
    Allows users to create a new real money trading account.
    Users can have multiple real accounts from different brokers.
    """
    model = RealAccount
    template_name = 'account_statement/real/account_create.html'
    fields = [
        'brokerage_provider', 
        'external_account_id', 
        'account_nickname',
        'base_currency',
        'day_trading_enabled',
        'margin_enabled',
        'options_level',
        'daily_loss_limit',
        'position_size_limit'
    ]
    success_url = reverse_lazy('account_statement:real_list')
    
    def form_valid(self, form):
        messages.success(
            self.request, 
            'Real money account created successfully! Please verify your account to enable trading.'
        )
        return super().form_valid(form)


class RealAccountUpdateView(AccountOwnerMixin, UpdateView):
    """
    Update view for real money trading accounts.
    
    Allows users to update their real account settings.
    """
    model = RealAccount
    template_name = 'account_statement/real/account_update.html'
    fields = [
        'account_nickname',
        'day_trading_enabled',
        'margin_enabled', 
        'options_level',
        'daily_loss_limit',
        'position_size_limit',
        'api_enabled'
    ]
    
    def get_success_url(self):
        return reverse_lazy('account_statement:real_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Real account updated successfully!')
        return super().form_valid(form)


@login_required
def real_account_sync(request, pk):
    """
    Sync a real money account with brokerage API.
    
    This updates account balances and positions from the brokerage.
    """
    account = get_object_or_404(RealAccount, pk=pk, user=request.user)
    
    if not account.api_enabled:
        messages.error(request, 'API access is not enabled for this account.')
        return redirect('account_statement:real_detail', pk=account.pk)
    
    if request.method == 'POST':
        try:
            success = account.sync_with_brokerage()
            if success:
                messages.success(
                    request, 
                    f'Account synced successfully! Last sync: {account.last_sync_date.strftime("%Y-%m-%d %H:%M")}'
                )
            else:
                messages.warning(request, 'Sync completed with warnings. Check account details.')
        except Exception as e:
            messages.error(request, f'Error syncing account: {str(e)}')
        
        return redirect('account_statement:real_detail', pk=account.pk)
    
    context = {
        'account': account,
        'page_title': 'Sync Real Account',
        'last_sync': account.last_sync_date,
        'sync_errors': account.sync_errors,
    }
    
    return render(request, 'account_statement/real/account_sync_confirm.html', context)


@login_required
def real_account_verify(request, pk):
    """
    Verify a real money account with brokerage.
    
    This initiates the account verification process.
    """
    account = get_object_or_404(RealAccount, pk=pk, user=request.user)
    
    if account.is_verified:
        messages.info(request, 'This account is already verified.')
        return redirect('account_statement:real_detail', pk=account.pk)
    
    if request.method == 'POST':
        # This would integrate with actual brokerage verification API
        # For now, we'll just mark as verified (placeholder)
        from django.utils import timezone
        account.is_verified = True
        account.verification_date = timezone.now()
        account.save()
        
        messages.success(request, 'Account verification initiated! You will receive confirmation via email.')
        return redirect('account_statement:real_detail', pk=account.pk)
    
    context = {
        'account': account,
        'page_title': 'Verify Real Account',
        'brokerage_name': account.get_brokerage_provider_display(),
    }
    
    return render(request, 'account_statement/real/account_verify.html', context)


@login_required
def real_account_risk_status(request, pk):
    """
    AJAX endpoint for real account risk management data.
    
    Returns JSON data for risk monitoring and alerts.
    """
    account = get_object_or_404(RealAccount, pk=pk, user=request.user)
    risk_status = account.get_risk_status()
    
    # Add additional real-account-specific metrics
    risk_status.update({
        'account_type': 'real',
        'is_verified': account.is_verified,
        'can_day_trade': account.can_day_trade(),
        'can_trade_options': account.can_trade_options(),
        'can_use_margin': account.can_use_margin(),
        'last_sync': account.last_sync_date.isoformat() if account.last_sync_date else None,
        'sync_errors': account.sync_errors,
    })
    
    return JsonResponse(risk_status)


class RealAccountViewSet(BaseAccountViewSet):
    """
    API ViewSet for real money trading accounts.
    
    Provides REST API endpoints for real account management.
    """
    queryset = RealAccount.objects.all()
    # serializer_class = RealAccountSerializer  # Would need to create this
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """
        Sync account with brokerage API.
        
        POST /api/real-accounts/{id}/sync/
        """
        account = self.get_object()
        
        if not account.api_enabled:
            return Response(
                {'error': 'API access is not enabled for this account'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            success = account.sync_with_brokerage()
            
            return Response({
                'message': 'Account sync initiated',
                'success': success,
                'last_sync': account.last_sync_date.isoformat() if account.last_sync_date else None,
                'sync_errors': account.sync_errors,
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to sync account: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """
        Initiate account verification.
        
        POST /api/real-accounts/{id}/verify/
        """
        account = self.get_object()
        
        if account.is_verified:
            return Response(
                {'message': 'Account is already verified'}, 
                status=status.HTTP_200_OK
            )
        
        try:
            # This would integrate with actual verification API
            from django.utils import timezone
            account.is_verified = True
            account.verification_date = timezone.now()
            account.save()
            
            return Response({
                'message': 'Account verification initiated',
                'verification_date': account.verification_date.isoformat(),
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to verify account: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def risk_status(self, request, pk=None):
        """
        Get risk management status.
        
        GET /api/real-accounts/{id}/risk_status/
        """
        account = self.get_object()
        risk_status = account.get_risk_status()
        
        return Response(risk_status)
    
    def get_queryset(self):
        """Ensure users only see their own real accounts."""
        return RealAccount.objects.filter(user=self.request.user)