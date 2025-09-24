from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

# API Overview
@api_view(['GET'])
def api_overview(request):
    """
    API Overview endpoint that provides information about available endpoints
    """
    api_urls = {
        'Overview': '/api/',
        'Statistics': '/api/stats/',
        'WorldClock': '/api/worldclock/',
        'Admin': '/admin/',
    }
    return Response(api_urls)

# Statistics endpoint
@api_view(['GET'])
def api_statistics(request):
    """
    Get statistics about the Thor application
    """
    # Return zeros/None for removed domains (backward compatible shape)
    stats = {
        'total_heroes': 0,
        'total_quests': 0,
        'completed_quests': 0,
        'total_artifacts': 0,
        'most_powerful_hero': None,
        'latest_quest': None,
    }
    return Response(stats, status=status.HTTP_200_OK)
