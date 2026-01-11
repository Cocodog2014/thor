from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def paper_status_view(_request):
    return Response({"detail": "Not implemented"}, status=501)
