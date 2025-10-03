from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def department_list(request):
    """List all departments"""
    return Response({'message': 'Department list endpoint'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def department_detail(request, department_id):
    """Get department details"""
    return Response({'message': f'Department {department_id} details'}, status=status.HTTP_200_OK)
