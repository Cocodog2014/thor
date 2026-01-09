"""GlobalMarkets API views."""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpRequest

from GlobalMarkets.models import Market


@api_view(['GET'])
def markets(request: HttpRequest):
    """Fetch all markets with key details."""
    qs = (
        Market.objects
        .all()
        .order_by('id')
        .values('id', 'key', 'name', 'status', 'status_changed_at')
    )
    return Response(list(qs), status=status.HTTP_200_OK)
