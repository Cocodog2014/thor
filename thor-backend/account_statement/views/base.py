"""
Base views for account statement functionality.

Contains shared views and mixins used by both paper and real account views.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models import AccountSummary


class AccountOwnerMixin(LoginRequiredMixin):
    """
    Mixin to ensure users can only access their own accounts.
    """
    
    def get_queryset(self):
        """Filter queryset to only show user's own accounts."""
        return super().get_queryset().filter(user=self.request.user)
    
    def form_valid(self, form):
        """Set the user to the current user when creating/updating."""
        if hasattr(form.instance, 'user'):
            form.instance.user = self.request.user
        return super().form_valid(form)


class AccountListView(AccountOwnerMixin, ListView):
    """
    Base list view for accounts.
    
    Shows all accounts belonging to the current user.
    """
    template_name = 'account_statement/account_list.html'
    context_object_name = 'accounts'
    paginate_by = 10
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['account_type'] = getattr(self, 'account_type', 'All')
        return context


class AccountDetailView(AccountOwnerMixin, DetailView):
    """
    Base detail view for accounts.
    
    Shows detailed information about a specific account.
    """
    template_name = 'account_statement/account_detail.html'
    context_object_name = 'account'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get recent summaries
        context['recent_summaries'] = self.object.summaries.all()[:10]
        
        # Calculate performance metrics
        if hasattr(self.object, 'get_performance_summary'):
            context['performance'] = self.object.get_performance_summary()
        
        return context


class AccountSummaryListView(LoginRequiredMixin, ListView):
    """
    List view for account summaries.
    
    Shows historical account summaries for a specific account.
    """
    model = AccountSummary
    template_name = 'account_statement/summary_list.html'
    context_object_name = 'summaries'
    paginate_by = 30
    
    def get_queryset(self):
        """Filter summaries for the specified account owned by current user."""
        # This will need to be implemented based on URL parameters
        return AccountSummary.objects.none()


@login_required
def account_dashboard(request):
    """
    Dashboard view showing overview of all user's accounts.
    """
    from ..models import PaperAccount, RealAccount
    
    # Get user's accounts
    paper_accounts = PaperAccount.objects.filter(user=request.user)
    real_accounts = RealAccount.objects.filter(user=request.user)
    
    context = {
        'paper_accounts': paper_accounts,
        'real_accounts': real_accounts,
        'total_accounts': paper_accounts.count() + real_accounts.count(),
    }
    
    return render(request, 'account_statement/dashboard.html', context)


class BaseAccountViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet for account API endpoints.
    
    Provides common functionality for both paper and real account APIs.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter to only show user's own accounts."""
        return self.queryset.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Set the user to the current user when creating."""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def summaries(self, request, pk=None):
        """Get account summaries for this account."""
        account = self.get_object()
        summaries = account.summaries.all()[:30]  # Last 30 summaries
        
        # This would need proper serialization
        data = [
            {
                'date': summary.statement_date.date(),
                'pnl_day': str(summary.pnl_day),
                'pnl_ytd': str(summary.pnl_ytd),
                'net_liquidating_value': str(summary.net_liquidating_value_snapshot),
            }
            for summary in summaries
        ]
        
        return Response(data)
    
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Get performance metrics for this account."""
        account = self.get_object()
        
        if hasattr(account, 'get_performance_summary'):
            performance = account.get_performance_summary()
            return Response(performance)
        
        return Response({'error': 'Performance data not available'}, 
                       status=status.HTTP_404_NOT_FOUND)