"""
Paper account specific views.

Contains views for managing paper trading accounts, including
account creation, reset functionality, and paper-specific features.
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
from ..models import PaperAccount


class PaperAccountListView(AccountListView):
    """
    List view for paper trading accounts.
    
    Shows all paper accounts belonging to the current user.
    """
    model = PaperAccount
    template_name = 'account_statement/paper/account_list.html'
    account_type = 'Paper'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Paper Trading Accounts'
        context['can_create'] = not self.get_queryset().exists()  # Only one paper account per user
        return context


class PaperAccountDetailView(AccountDetailView):
    """
    Detail view for paper trading accounts.
    
    Shows detailed information about a specific paper account
    including paper-specific features like reset functionality.
    """
    model = PaperAccount
    template_name = 'account_statement/paper/account_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Paper Account - {self.object.account_number}'
        context['can_reset'] = True  # Paper accounts can always be reset
        return context


class PaperAccountCreateView(AccountOwnerMixin, CreateView):
    """
    Create view for paper trading accounts.
    
    Allows users to create a new paper trading account.
    Users can only have one paper account.
    """
    model = PaperAccount
    template_name = 'account_statement/paper/account_create.html'
    fields = ['starting_balance', 'base_currency']
    success_url = reverse_lazy('account_statement:paper_list')
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user already has a paper account
        if PaperAccount.objects.filter(user=request.user).exists():
            messages.warning(request, 'You already have a paper trading account.')
            return redirect('account_statement:paper_list')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        messages.success(self.request, 'Paper trading account created successfully!')
        return super().form_valid(form)


class PaperAccountUpdateView(AccountOwnerMixin, UpdateView):
    """
    Update view for paper trading accounts.
    
    Allows users to update their paper account settings.
    """
    model = PaperAccount
    template_name = 'account_statement/paper/account_update.html'
    fields = ['starting_balance', 'base_currency']
    
    def get_success_url(self):
        return reverse_lazy('account_statement:paper_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Paper account updated successfully!')
        return super().form_valid(form)


@login_required
def paper_account_reset(request, pk):
    """
    Reset a paper trading account to its starting balance.
    
    This clears all positions and resets the account balance.
    """
    account = get_object_or_404(PaperAccount, pk=pk, user=request.user)
    
    if request.method == 'POST':
        try:
            account.reset_account()
            messages.success(
                request, 
                f'Paper account reset successfully! Balance restored to ${account.starting_balance:,.2f}'
            )
        except Exception as e:
            messages.error(request, f'Error resetting account: {str(e)}')
        
        return redirect('account_statement:paper_detail', pk=account.pk)
    
    context = {
        'account': account,
        'page_title': 'Reset Paper Account',
    }
    
    return render(request, 'account_statement/paper/account_reset_confirm.html', context)


@login_required
def paper_account_performance(request, pk):
    """
    AJAX endpoint for paper account performance data.
    
    Returns JSON data for charts and performance metrics.
    """
    account = get_object_or_404(PaperAccount, pk=pk, user=request.user)
    performance = account.get_performance_summary()
    
    # Add additional paper-specific metrics
    performance.update({
        'account_type': 'paper',
        'reset_count': account.reset_count,
        'last_reset': account.last_reset_date.isoformat() if account.last_reset_date else None,
    })
    
    return JsonResponse(performance)


class PaperAccountViewSet(BaseAccountViewSet):
    """
    API ViewSet for paper trading accounts.
    
    Provides REST API endpoints for paper account management.
    """
    queryset = PaperAccount.objects.all()
    # serializer_class = PaperAccountSerializer  # Would need to create this
    
    @action(detail=True, methods=['post'])
    def reset(self, request, pk=None):
        """
        Reset paper account to starting balance.
        
        POST /api/paper-accounts/{id}/reset/
        """
        account = self.get_object()
        
        try:
            old_balance = account.net_liquidating_value
            account.reset_account()
            
            return Response({
                'message': 'Account reset successfully',
                'old_balance': str(old_balance),
                'new_balance': str(account.net_liquidating_value),
                'reset_count': account.reset_count,
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to reset account: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def performance_chart(self, request, pk=None):
        """
        Get performance data formatted for charts.
        
        GET /api/paper-accounts/{id}/performance_chart/
        """
        account = self.get_object()
        
        # Get historical summaries for chart
        summaries = account.summaries.order_by('statement_date')[:90]  # Last 90 days
        
        chart_data = {
            'labels': [s.statement_date.strftime('%Y-%m-%d') for s in summaries],
            'datasets': [
                {
                    'label': 'Account Value',
                    'data': [float(s.net_liquidating_value_snapshot) for s in summaries],
                    'borderColor': 'rgb(75, 192, 192)',
                    'tension': 0.1
                },
                {
                    'label': 'Daily P&L',
                    'data': [float(s.pnl_day) for s in summaries],
                    'borderColor': 'rgb(255, 99, 132)',
                    'tension': 0.1
                }
            ]
        }
        
        return Response(chart_data)
    
    def get_queryset(self):
        """Ensure users only see their own paper accounts."""
        return PaperAccount.objects.filter(user=self.request.user)