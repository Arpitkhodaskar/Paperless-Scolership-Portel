from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scholarship_schemes(request):
    """List scholarship schemes"""
    return Response({'message': 'Scholarship schemes endpoint'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def disbursements(request):
    """List disbursements"""
    return Response({'message': 'Disbursements endpoint'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def budgets(request):
    """List budgets"""
    return Response({'message': 'Budgets endpoint'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transactions(request):
    """List transactions"""
    return Response({'message': 'Transactions endpoint'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_reports(request):
    """List financial reports"""
    return Response({'message': 'Financial reports endpoint'}, status=status.HTTP_200_OK)
