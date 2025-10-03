from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grievance_list(request):
    """List grievances"""
    return Response({'message': 'Grievance list endpoint'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_grievance(request):
    """Create new grievance"""
    return Response({'message': 'Create grievance endpoint'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grievance_detail(request, grievance_id):
    """Get grievance details"""
    return Response({'message': f'Grievance {grievance_id} details'}, status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def grievance_comments(request, grievance_id):
    """Get or add grievance comments"""
    return Response({'message': f'Grievance {grievance_id} comments'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grievance_categories(request):
    """List grievance categories"""
    return Response({'message': 'Grievance categories endpoint'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def faqs(request):
    """List FAQs"""
    return Response({'message': 'FAQs endpoint'}, status=status.HTTP_200_OK)
